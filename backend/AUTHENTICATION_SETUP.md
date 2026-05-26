# Authentication Setup Guide

## JWT Secret Key Configuration

The backend requires a `JWT_SECRET_KEY` environment variable to be set for proper authentication. Without this, token refresh will fail with 401 errors.

### Issue Symptoms
- 401 Unauthorized errors on `/api/v1/cover-letters` and other protected endpoints
- POST `/api/v1/auth/refresh` returning 401 Unauthorized
- Users unable to maintain authentication sessions

### Solution

Set the `JWT_SECRET_KEY` environment variable in your deployment environment:

```bash
# Generate a secure random key
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Or use Python
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### Deployment Platforms

#### Render
1. Go to your Render dashboard
2. Navigate to your backend service
3. Go to "Environment" section
4. Add environment variable:
   - Key: `JWT_SECRET_KEY`
   - Value: `<your-generated-secure-key>`

#### Docker
Add to your `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - JWT_SECRET_KEY=your-generated-secure-key-here
```

#### Local Development
Create a `.env` file in the backend directory:
```
JWT_SECRET_KEY=your-generated-secure-key-here
```

**Important:** Never commit the `.env` file or expose the JWT secret key in public repositories.

### Verification

After setting the environment variable, restart your backend service. The authentication should work correctly and token refresh should succeed.

### Troubleshooting

If you still see 401 errors after setting the JWT_SECRET_KEY:

1. Check the backend logs for detailed error messages (we've added enhanced logging)
2. Ensure the environment variable is actually loaded by the backend
3. Verify users are logging out and logging back in to get new tokens signed with the new key
4. Clear localStorage in the frontend to remove old tokens signed with the old key
