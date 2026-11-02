# ChatGPT Plugins (OpenAI) — fit for Tru8

2026-11-02 · research only, nothing built or submitted. A research agent read OpenAI's docs. Items marked *unconfirmed* have no primary source.

## What it is
- OpenAI now calls third-party integrations **Plugins**, listed in the **ChatGPT Directory**, which is shared with Codex. Docs: developers.openai.com/plugins (the old /apps-sdk URLs redirect there). A plugin is one remote MCP server, plus optional skills, plus optional UI.
- Timeline: app submissions opened 2025-12-17. Approved apps became Codex plugins on 2026-03-25 (plugins changelog). The rename from "Apps" to "Plugins" was around 2026-07-09 (*unconfirmed*: third-party blogs only).
- Open to third parties, through a review.
- Countries are chosen with `publication.countries`. **GB is available**: an OpenAI support reply on 2026-10-14 mentions a plugin approved for US, CA and GB. Whether EU users can use plugins is *unconfirmed*. Projects with EU data residency cannot submit.

## Requirements
- **Transport:** a remote streamable-HTTP MCP server at a stable public HTTPS address. Our `https://api.trueight.com/mcp/` qualifies. The address cannot change later without creating a new plugin.
- **Auth:** only **none or OAuth 2.1**. API keys, bearer tokens and custom headers are rejected (developers.openai.com/plugins/build/auth).
  - The OAuth flow is authorization code with PKCE S256.
  - The server must publish `/.well-known/oauth-protected-resource` and authorization server metadata.
  - ChatGPT registers itself as a client using CIMD (preferred) or dynamic client registration.
  - The token audience must match the `resource` parameter.
  - Each tool declares its auth in `securitySchemes`.
- **Tool metadata:**
  - `readOnlyHint`, `destructiveHint` and `openWorldHint` must each be set explicitly, with a justification.
  - A tool must not tell the model to call another tool.
  - Responses should not carry internal IDs unless they are needed.
- **Timeout:** *unconfirmed*. Developers on the forum report about **60 s** per tool call.
- **Submission:**
  - Done in the OpenAI Platform dashboard, with individual or business identity verification and domain verification.
  - Needs a website, support page, privacy policy and terms.
  - Needs 5 positive and 3 negative test cases, a demo video, and a reviewer test account with no MFA.
  - Trial or demo plugins are rejected. No fees are documented (*unconfirmed*).
- **Money** (plugin-guidelines.md, build/monetization.md):
  - A plugin may **not sell digital goods, subscriptions or credits** inside ChatGPT, and must not show upgrade prompts.
  - It may let users use what they already pay for elsewhere.
  - No ChatGPT-only prices and no ads.

## What it would take for Tru8 (most effort first)
1. **Blocker: an OAuth 2.1 authorization server.** It must link a ChatGPT user to their Tru8 account and credits. Needed: PKCE, CIMD or dynamic registration, both metadata documents, token checking on `/mcp` (signature, issuer, audience), and mapping each token to a Tru8 user. *Open question:* can Clerk act as the authorization server (OAuth provider, dynamic registration or CIMD)? Check before designing our own.
2. **Likely blocker: timeout.**
   - `tru8_check` now polls inside the tool for up to about 7 minutes. Against a 60 s limit, a full check (60–120 s) fails.
   - Needed: a ChatGPT mode that returns the check ID within about 50 s, then a way to fetch the result.
   - The rule against one tool telling the model to call another makes the follow-up call a design question. A widget that polls through `callTool` is one route.
3. **Money wording.**
   - When credits run out, the response must say so neutrally, with no purchase link.
   - Prices must be the same as everywhere else, which they already are.
   - Users must already have credits or Console. ChatGPT cannot be a place to sign up and pay.
4. **Listing items.**
   - Identity verification and domain verification.
   - Terms and support pages: check they exist and are current.
   - Demo video and 8 test cases.
   - A no-MFA reviewer account with credits.
5. **Annotations.** `tru8_check` is already `readOnlyHint=False`, `openWorldHint=True`. The question is whether a charge makes it `destructiveHint=True`; it is currently False and needs a justification either way. Also audit the responses for internal IDs.

## Commercial note
ChatGPT can only be a way in for users who already pay Tru8. It cannot sign up new paying users inside ChatGPT. Users would find Tru8 in the directory, then have to buy credits on trueight.com before it works.

## Next step
This is difficulty ≥3 (auth plus a protocol change), so it needs a design and review before any build. Step one: check whether Clerk can be the OAuth server. That decides whether this is days or weeks of work.
