---
name: csharp-rest-api
version: 1.0.0
description: Best practices for C# .NET 8 REST APIs — Clean Architecture, JWT/cookies auth, roles, DTOs, validation, EF Core
shared_directive: If the project includes C#/.NET endpoints, read `.agent/skills/csharp-rest-api/SKILL.md` before implementing any endpoint.
category: stack
applies_to: [csharp, dotnet, dotnet8, rest-api, clean-architecture, ef-core]
scripts: []
depends_on: []
min_toolkit_version: 1.0.0
---

# C# REST API — Best practices (.NET 8 / Clean Architecture)

## Layer structure

```
Domain/          → Entities, value objects, repository interfaces, enums.
                   No external dependencies. No EF Core references.
Application/     → Use cases (commands/queries), DTOs, service interfaces.
                   Depends only on Domain. No EF Core or HTTP references.
Infrastructure/  → Implementations: repositories (EF Core), external services, DbContext.
                   Depends on Application and Domain.
API/             → Controllers, middlewares, Program.cs, configuration.
                   Depends on Application and Infrastructure.
```

**Layer rules:**
- Controllers never access repositories directly. Always via Application.
- Domain never imports EF Core namespaces (`Microsoft.EntityFrameworkCore`).
- Application never imports Infrastructure namespaces.
- DTOs live in Application, not Domain.

---

## Authentication — JWT with HttpOnly Cookies

### Configuration (Program.cs)

```csharp
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Secret"]!)),
            ValidateIssuer = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidateAudience = true,
            ValidAudience = builder.Configuration["Jwt:Audience"],
            ValidateLifetime = true,
            ClockSkew = TimeSpan.Zero
        };
        // Read token from HttpOnly cookie
        options.Events = new JwtBearerEvents
        {
            OnMessageReceived = ctx =>
            {
                ctx.Token = ctx.Request.Cookies["access_token"];
                return Task.CompletedTask;
            }
        };
    });
```

### Emit token as HttpOnly cookie

```csharp
private void SetAuthCookies(HttpResponse response, string accessToken, string refreshToken)
{
    var cookieOptions = new CookieOptions
    {
        HttpOnly = true,
        Secure = true,          // HTTPS only in production
        SameSite = SameSiteMode.Strict,
        Expires = DateTimeOffset.UtcNow.AddMinutes(15)
    };
    response.Cookies.Append("access_token", accessToken, cookieOptions);

    var refreshOptions = new CookieOptions
    {
        HttpOnly = true,
        Secure = true,
        SameSite = SameSiteMode.Strict,
        Path = "/api/auth/refresh",  // only the refresh endpoint
        Expires = DateTimeOffset.UtcNow.AddDays(7)
    };
    response.Cookies.Append("refresh_token", refreshToken, refreshOptions);
}
```

---

## Role-based authorization

```csharp
// Define role claims in the token
var claims = new List<Claim>
{
    new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
    new Claim(ClaimTypes.Email, user.Email),
    new Claim(ClaimTypes.Role, user.Role.ToString())
};

// Protect endpoints
[Authorize(Roles = "Admin,Supervisor")]
[HttpPost("transfer")]
public async Task<IActionResult> TransferWeapon(...)

[Authorize]  // any authenticated role
[HttpGet("my-profile")]
public async Task<IActionResult> GetMyProfile(...)
```

---

## DTOs and validation

```csharp
// Always validate in the DTO, not the controller
public record CreateWeaponDto
{
    [Required]
    [StringLength(100, MinimumLength = 2)]
    public string SerialNumber { get; init; } = string.Empty;

    [Required]
    public WeaponType Type { get; init; }

    [Range(1900, 2100)]
    public int ManufactureYear { get; init; }
}

// Minimal controller
[HttpPost]
public async Task<IActionResult> Create([FromBody] CreateWeaponDto dto)
{
    // ModelState already validated by [ApiController]
    var result = await _mediator.Send(new CreateWeaponCommand(dto));
    return result.IsSuccess
        ? CreatedAtAction(nameof(GetById), new { id = result.Value }, result.Value)
        : BadRequest(result.Error);
}
```

**Rule:** Never expose Domain entities directly in the response. Always response DTOs.

---

## Consistent error responses (ProblemDetails)

```csharp
// Program.cs
builder.Services.AddProblemDetails();

// In middlewares or exception handlers:
return TypedResults.Problem(
    detail: "Weapon not found.",
    statusCode: StatusCodes.Status404NotFound,
    title: "Resource not found"
);
```

**HTTP codes:**
- `200 OK` → successful read
- `201 Created` → resource created (include `Location` header)
- `204 No Content` → successful operation without body
- `400 Bad Request` → validation failed
- `401 Unauthorized` → not authenticated
- `403 Forbidden` → authenticated but no permission
- `404 Not Found` → resource doesn't exist
- `409 Conflict` → state conflict (e.g. duplicate serial)
- `500 Internal Server Error` → unhandled error

---

## EF Core — safe patterns

```csharp
// Use AsNoTracking() for reads
var weapons = await _context.Weapons
    .AsNoTracking()
    .Where(w => w.Status == WeaponStatus.Active)
    .Select(w => new WeaponSummaryDto(w.Id, w.SerialNumber, w.Type))
    .ToListAsync(cancellationToken);

// Soft delete — never delete physically in institutional systems
public class Weapon : BaseEntity
{
    public bool IsDeleted { get; private set; }
    public DateTime? DeletedAt { get; private set; }

    public void Delete()
    {
        IsDeleted = true;
        DeletedAt = DateTime.UtcNow;
    }
}

// Global query filter for soft delete
modelBuilder.Entity<Weapon>().HasQueryFilter(w => !w.IsDeleted);
```

---

## Security — per-endpoint checklist

Before closing any endpoint, verify:
- [ ] Requires `[Authorize]` or has explicit reason to be public.
- [ ] Authorized roles restricted to the minimum necessary.
- [ ] Inputs validated with Data Annotations or FluentValidation.
- [ ] No stack trace exposed in production (`ASPNETCORE_ENVIRONMENT != Development`).
- [ ] No returning other users' data without ownership check.
- [ ] Parameterized queries (EF Core protects against SQL injection by default).

---

## Naming conventions

```
Controllers:   WeaponsController, AuthController
Commands:      CreateWeaponCommand, TransferWeaponCommand
Queries:       GetWeaponByIdQuery, GetWeaponsListQuery
Handlers:      CreateWeaponCommandHandler
DTOs:          CreateWeaponDto (request), WeaponDto (response), WeaponSummaryDto
Entities:      Weapon, User, Transfer (PascalCase, singular)
DbContext:     AppDbContext
Repositories:  IWeaponRepository, WeaponRepository
```

---

## Configuration that NEVER goes in code

Always in `appsettings.json` (non-sensitive) or env vars / secrets (sensitive):

```json
// appsettings.json — non-sensitive
{
  "Jwt": {
    "Issuer": "arsenal-api",
    "Audience": "arsenal-client",
    "ExpirationMinutes": 15
  }
}
```

```bash
# Env vars or dotnet user-secrets — NEVER in code
Jwt__Secret=<long-random-key>
ConnectionStrings__DefaultConnection=<connection-string>
```
