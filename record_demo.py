import asyncio
import os
import shutil
from playwright.async_api import async_playwright
from PIL import Image
import imageio

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

        # 1. Prompt 1: Ask what's in customer table in BigQuery
        prompt1 = "What's in customer table in BigQuery?"
        print(f"Submitting Prompt 1: {prompt1}")
        await page.fill("#input", prompt1)
        await page.click("form#form button[type='submit']")
        
        print("Waiting for agent response to Prompt 1...")
        # Wait until 2nd agent message is present and not "…"
        await page.wait_for_function('document.querySelectorAll(".msg.agent").length >= 2 && !document.querySelectorAll(".msg.agent")[1].textContent.includes("…")', timeout=60000)
        await page.evaluate('document.getElementById("log").scrollTop = document.getElementById("log").scrollHeight')
        await page.wait_for_timeout(6000)

        # 2. Prompt 2: Generate CSV of test data for that table
        prompt2 = "Generate a CSV of test data for customer_data.customers table"
        print(f"Submitting Prompt 2: {prompt2}")
        await page.fill("#input", prompt2)
        await page.click("form#form button[type='submit']")

        print("Waiting for agent response to Prompt 2...")
        # Wait until 3rd agent message is present and not "…"
        await page.wait_for_function('document.querySelectorAll(".msg.agent").length >= 3 && !document.querySelectorAll(".msg.agent")[2].textContent.includes("…")', timeout=60000)
        await page.evaluate('document.getElementById("log").scrollTop = document.getElementById("log").scrollHeight')
        await page.wait_for_timeout(8000)

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

            # Generate demo.gif
            print("Converting recording to demo.gif...")
            reader = imageio.get_reader(target_path)
            frames = []
            for i, frame in enumerate(reader):
                if i % 8 == 0:
                    img = Image.fromarray(frame).resize((640, 360), Image.Resampling.NEAREST)
                    frames.append(img)
            if frames:
                frames[0].save(
                    "demo.gif",
                    save_all=True,
                    append_images=frames[1:],
                    optimize=True,
                    duration=300,
                    loop=0
                )
                print("Successfully updated demo.gif!")

if __name__ == "__main__":
    asyncio.run(record_demo())
