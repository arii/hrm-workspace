### 2. Non-Standard Analysis: The "Sidecar" Token Delivery

You are using a `jwt` callback in NextAuth to "leak" the refresh token to a local file via an internal API call (`/internal/token-delivery`).

  * **Your Approach:** Frontend logs in -> NextAuth gets Token -> NextAuth POSTs token to Backend -> Backend saves to `json` file.
  * **The Standard Approach:** Frontend logs in -> NextAuth saves Token to **Database** -> Backend reads Token from **Database**.

#### Why your current approach is risky:

1.  **Race Conditions:** If the user refreshes the page quickly, NextAuth might trigger multiple `jwt` callbacks, spamming your internal endpoint and potentially saving an older/invalid token over a newer one.
2.  **Filesystem Instability:** You are saving tokens to `logs/spotify_tokens.json`.
      * **In Docker/Kubernetes:** This file will be wiped every time you deploy or restart the container.
      * **In Serverless (Vercel):** You *cannot* write to the filesystem. This architecture is fundamentally incompatible with Vercel deployment for the backend portion.
3.  **Synchronization Drift:** If the background service refreshes the token (updating the JSON file), but the user comes back to the Next.js app 1 hour later, NextAuth might still have the *old* token in its encrypted cookie. When NextAuth tries to use it, it fails, and since it doesn't know about the new token in the JSON file, the user is forced to re-login.

### 3. Recommended Architecture: NextAuth Database Adapter

To fix the synchronization and filesystem issues, you should move to a **Database Adapter** (e.g., Prisma with PostgreSQL/SQLite or MongoDB).

**The Flow:**

1.  NextAuth saves the `Account` (access_token, refresh_token) to the `Account` table in your DB automatically.
2.  Your background service (`spotifyTokenManager.ts`) simply queries the DB for the user's latest token.
3.  If the background service refreshes the token, it updates the DB row.
4.  Next time the user visits the frontend, NextAuth reads the *updated* token from the DB.

### 4. Code Improvement Plan

If you cannot switch to a Database immediately and must stick to this file-based approach (e.g., for a purely local Raspberry Pi setup), apply these fixes:

#### A. Fix the URL in `lib/auth.ts`

```typescript
// File: lib/auth.ts
async function refreshAccessToken(token: JWT) {
  try {
    // FIX: Use the correct Spotify endpoint
    const url = 'https://accounts.spotify.com/api/token' 
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: 'Basic ' + Buffer.from(process.env.SPOTIFY_CLIENT_ID + ':' + process.env.SPOTIFY_CLIENT_SECRET).toString('base64'),
      },
      // ... rest of body
    })
    // ...
```

#### B. Remove Unused PKCE Code

You uploaded `utils/pkce.ts`. NextAuth's Spotify Provider uses the "Authorization Code Flow" (Confidential Client) which relies on `client_secret` stored on the server. You are **not** using PKCE (which is for public clients like mobile apps or SPAs without a backend).

  * **Action:** You can delete `utils/pkce.ts`. It is dead code.

#### C. Robust File Handling (If keeping the JSON file)

Your `SpotifyTokenManager` overwrites the file blindly. Ensure you use atomic writes to prevent corruption if the server crashes mid-write.

```typescript
// services/spotifyTokenManager.ts
import fs from 'fs'
import path from 'path'

// Helper for atomic writes
const writeTokenFileSafe = (filePath: string, data: any) => {
  const tempPath = `${filePath}.tmp`
  fs.writeFileSync(tempPath, JSON.stringify(data, null, 2))
  fs.renameSync(tempPath, filePath) // Atomic rename
}
```

### Summary of Tasks

1.  **IMMEDIATE:** Change `https://accounts.spotify.com/api/token` to `https://accounts.spotify.com/api/token` in both `lib/auth.ts` and `services/spotifyTokenManager.ts`.
2.  **CLEANUP:** Delete `utils/pkce.ts`.
3.  **ARCHITECT:** Decide if you want to persist with the JSON file sidecar (Local only) or switch to a Database Adapter (Production/Scalable).

**Developer Question:**
Are you planning to deploy this application to a cloud provider (Vercel, AWS, DigitalOcean), or is this strictly a local-network device (like a Raspberry Pi running in your gym)? This dictates whether we *must* rip out the filesystem code.

---
*This issue consolidates the information from #928, #927, #926, and #925, which will be closed as duplicates.*
