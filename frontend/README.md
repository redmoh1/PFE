<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/drive/1ViKGbwYIVdkpM20DtAoNICjG7CuDGa9o

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Configure the backend URL (recommended):
   - Create `.env.local` and set `VITE_API_TARGET=http://localhost:8002` (used by the Vite dev proxy)
   - Optional: set `VITE_API_BASE=http://localhost:8002` if you want the frontend to call the backend directly (no proxy)
   - Do not set `VITE_API_BASE=/api` (inventory endpoints are under `/inventory`, not `/api/inventory`)
3. Run the app:
   `npm run dev`
