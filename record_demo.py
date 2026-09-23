import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def record_demo():
    video_dir = "demo_videos"
    os.makedirs(video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720},
        )

        page = await context.new_page()
        print("Navigating to local frontend http://localhost:8080...")
        await page.goto("http://localhost:8080", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 1. Prompt 1: Profile novasmart_pricing.inventory table and generate CSV
        prompt1 = "Profile novasmart_pricing.inventory table and generate 30 synthetic rows as CSV"
        print(f"Submitting Prompt 1: {prompt1}")
        await page.fill("#input", prompt1)
        await page.click("form#form button[type='submit']")
        
        print("Waiting for agent response to Prompt 1...")
        await page.wait_for_timeout(30000)

        # 2. Prompt 2: Rich multi-tool prompt with Omni visualization video generation
        prompt2 = "Generate a short visualization video for table novasmart_pricing.inventory using Google Omni model"
        print(f"Submitting Prompt 2: {prompt2}")
        await page.fill("#input", prompt2)
        await page.click("form#form button[type='submit']")

        print("Waiting for agent response to Prompt 2...")
        await page.wait_for_timeout(30000)

        # Save video path
        video_page = page.video
        await context.close()
        await browser.close()

        if video_page:
            video_path = await video_page.path()
            target_path = os.path.join(video_dir, "agent_demo.webm")
            shutil.copy(video_path, target_path)
            artifact_path = "/config/.gemini/antigravity/brain/bdf7da65-920b-4d71-9c33-2cbd14521e92/agent_demo.webm"
            shutil.copy(video_path, artifact_path)
            print(f"Demo video saved to: {target_path} and artifact: {artifact_path}")

if __name__ == "__main__":
    asyncio.run(record_demo())
