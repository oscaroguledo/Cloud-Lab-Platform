# OAuth Setup: Google & Microsoft

Both are **completely free**. Here's how to set them up:

## Google OAuth Setup (5 minutes)

### 1. Create Google Cloud Project
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Click "Select a Project" → "New Project"
- Name it: `Cloud-Lab-Platform`
- Wait for creation

### 2. Enable OAuth Consent Screen
- Left sidebar → "OAuth consent screen"
- Select "External" → Create
- Fill in:
  - **App name**: Cloud Lab Platform
  - **User support email**: your-email@gmail.com
  - **Developer contact**: your-email@gmail.com
- Click "Save and Continue"
- Skip scopes, click "Save and Continue"
- Review and click "Back to Dashboard"

### 3. Create OAuth Credentials
- Left sidebar → "Credentials"
- Click "Create Credentials" → "OAuth client ID"
- Choose "Web application"
- Add Authorized redirect URIs:
  ```
  http://localhost:8000/api/v1/auth/callback/google
  https://yourdomain.com/api/v1/auth/callback/google
  ```
- Click Create
- Copy **Client ID** and **Client Secret**

### 4. Add to `.env`
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback/google
```

---

## Microsoft/Azure AD Setup (10 minutes)

### 1. Register Application
- Go to [Azure Portal](https://portal.azure.com/)
- Search for "App registrations" → New registration
- Fill in:
  - **Name**: Cloud Lab Platform
  - **Supported account types**: Accounts in this organizational directory only
  - **Redirect URI**: Web
    ```
    http://localhost:8000/api/v1/auth/callback/microsoft
    ```
- Click Register

### 2. Get Credentials
- Left panel → "Certificates & secrets"
- Click "New client secret"
- Add with 24 months expiry
- Copy the **Value** (this is your secret)
- Go back to Overview tab
- Copy **Application (client) ID**

### 3. Add Redirect URIs
- Left panel → "Authentication"
- Under "Web", add redirect URIs:
  ```
  http://localhost:8000/api/v1/auth/callback/microsoft
  https://yourdomain.com/api/v1/auth/callback/microsoft
  ```
- Enable "Access tokens" and "ID tokens"
- Save

### 4. Add to `.env`
```
MICROSOFT_CLIENT_ID=your-app-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback/microsoft
MICROSOFT_TENANT=common
```

---

## Backend Implementation

### OAuth Flow (High Level)

```
1. User clicks "Login with Google/Microsoft"
   ↓
2. Redirect to provider's login page
   ↓
3. User approves access
   ↓
4. Provider redirects back with `code` parameter
   ↓
5. Backend exchanges `code` for access token
   ↓
6. Backend fetches user info from provider
   ↓
7. Check if user exists:
   - If yes: Return JWT tokens → Login complete
   - If no: Create user + SSO connection → Login complete
```

### Example Endpoint

```python
@router.post("/auth/callback/google")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    # 1. Exchange code for tokens
    token_response = await exchange_google_code(code)
    
    # 2. Get user info from Google
    user_info = await get_google_user_info(token_response["access_token"])
    
    # 3. Handle SSO callback
    oauth_handler = OAuthHandler()
    user, is_new = await oauth_handler.handle_google_callback(
        db,
        user_info,
        org_id=request.user_org_id,  # or from query param
    )
    
    # 4. Create session and tokens
    session = await session_service.create_session(db, user.id)
    access_token = await auth_service.create_access_token(settings, user, session)
    refresh_token = await auth_service.create_refresh_token(settings, user, session, jti)
    
    # 5. Return tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": str(user.id),
        "is_new_user": is_new,
    }
```

---

## Libraries Needed

```bash
pip install httpx  # For making OAuth requests
pip install python-jose[cryptography]  # Already have for JWT
```

---

## Flow Summary

| Step | Google | Microsoft |
|------|--------|-----------|
| **Setup** | Google Cloud Console | Azure Portal |
| **Cost** | Free | Free |
| **Time** | 5 min | 10 min |
| **Users** | Anyone with Google account | Office 365 users + Microsoft accounts |
| **Best for** | Individual users | Enterprise |

---

## Security Notes

- **Keep secrets safe**: Never commit to git
- **Use HTTPS in production**: OAuth requires HTTPS
- **State parameter**: Prevents CSRF attacks (included in schema)
- **Email verification**: Check if `email_verified` from provider
- **Token refresh**: Store refresh token securely if needed

---

## Testing Locally

```bash
# Dev environment
export GOOGLE_CLIENT_ID=xxx
export GOOGLE_CLIENT_SECRET=yyy
export GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback/google

# Frontend would redirect to:
# https://accounts.google.com/o/oauth2/v2/auth?
#   client_id=YOUR_ID&
#   redirect_uri=http://localhost:8000/api/v1/auth/callback/google&
#   response_type=code&
#   scope=openid%20email%20profile&
#   state=random_state_value
```
