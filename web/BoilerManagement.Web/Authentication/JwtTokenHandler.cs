using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace BoilerManagement.Web.Authentication;

public static class JwtTokenHandler
{
    private static readonly JwtSecurityTokenHandler _handler = new();

    /// <summary>Returns claims from a JWT, or null if the token is invalid/expired.</summary>
    public static ClaimsPrincipal? ParseToken(string? token)
    {
        if (string.IsNullOrWhiteSpace(token))
            return null;

        try
        {
            var jwt = _handler.ReadJwtToken(token);

            // Reject if expired (with 30-second clock skew tolerance)
            if (jwt.ValidTo < DateTime.UtcNow.AddSeconds(-30))
                return null;

            var claims = new List<Claim>(jwt.Claims);

            // FastAPI / python-jose stores roles in the "role" claim (may be repeated)
            // Ensure Microsoft ClaimTypes.Role claims are present for AuthorizeView
            var roleClaims = claims
                .Where(c => c.Type == "role" || c.Type == ClaimTypes.Role)
                .Select(c => c.Value)
                .Distinct()
                .ToList();

            foreach (var role in roleClaims)
                if (!claims.Any(c => c.Type == ClaimTypes.Role && c.Value == role))
                    claims.Add(new Claim(ClaimTypes.Role, role));

            // Map "sub" → NameIdentifier if not already present
            var sub = jwt.Subject;
            if (!string.IsNullOrEmpty(sub) && !claims.Any(c => c.Type == ClaimTypes.NameIdentifier))
                claims.Add(new Claim(ClaimTypes.NameIdentifier, sub));

            var identity = new ClaimsIdentity(claims, "jwt");
            return new ClaimsPrincipal(identity);
        }
        catch
        {
            return null;
        }
    }

    public static bool IsExpired(string? token)
    {
        if (string.IsNullOrWhiteSpace(token)) return true;
        try
        {
            var jwt = _handler.ReadJwtToken(token);
            return jwt.ValidTo < DateTime.UtcNow.AddSeconds(-30);
        }
        catch { return true; }
    }
}
