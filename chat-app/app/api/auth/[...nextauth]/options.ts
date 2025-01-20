/** 
 * Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { AuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

/* eslint-disable @typescript-eslint/no-explicit-any */

const authOptions: AuthOptions = {
    providers: [
      KeycloakProvider({
        clientId: process.env.KEYCLOAK_CLIENT_ID!, // Use the front-end client ID here
        issuer: process.env.KEYCLOAK_ISSUER,
        clientSecret: process.env.KEYCLOAK_CLIENT_SECRET!, // Set the client secret
        authorization: {
          params: {
            scope: "openid email profile offline_access",
          },
        },
      }),
    ],
    callbacks: {
      async jwt({ token, account, user }) {
        // Initial sign in
        if (account && user) {
          return {
            ...token,
            accessToken: account.access_token,
            refreshToken: account.refresh_token,
            accessTokenExpires: account.expires_at! * 1000, // Convert to milliseconds
          };
        }
  
        // Return previous token if the access token has not expired yet
        if (Date.now() < token.accessTokenExpires!) {
          return token;
        }
  
        // Access token has expired, try to update it
        return refreshAccessToken(token);
      },
      async session({ session, token }) {
        session.access_token = token.accessToken;
        session.error = token.error;
        return session;
      },
    },
  };

  /**
 * Takes a token, and returns a new token with updated
 * `accessToken` and `accessTokenExpires`. If an error occurs,
 * returns the old token and an error property
 */
async function refreshAccessToken(token: any) {
    try {
      const response = await fetch(`${process.env.KEYCLOAK_ISSUER}/protocol/openid-connect/token`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        method: 'POST',
        body: new URLSearchParams({
          client_id: process.env.KEYCLOAK_CLIENT_ID!,
          client_secret: process.env.KEYCLOAK_CLIENT_SECRET!,
          grant_type: 'refresh_token',
          refresh_token: token.refreshToken,
        }),
      });
  
      const refreshedTokens = await response.json();
  
      if (!response.ok) {
        throw refreshedTokens;
      }
  
      return {
        ...token,
        accessToken: refreshedTokens.access_token,
        accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
        refreshToken: refreshedTokens.refresh_token ?? token.refreshToken, // Fall back to old refresh token
      };
    } catch (error) {
      console.log("Token refresh failed:", error);
  
      return {
        ...token,
        error: "RefreshAccessTokenError",
      };
    }
  }

  export { authOptions };