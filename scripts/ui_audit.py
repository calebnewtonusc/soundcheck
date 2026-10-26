"""Screenshot every screen at 6 widths (390 to 1920). Run against a local server: python scripts/ui_audit.py <outdir>.
2026-10-26: the join screen broke at 1024 to 1400 wide after only phone + 1440 were checked."""
import asyncio, sys, json, urllib.request
from playwright.async_api import async_playwright
B="http://127.0.0.1:8888"; OUT=sys.argv[1] if len(sys.argv)>1 else "/private/tmp/claude-501/sc/audit"
WIDTHS=[390,768,1024,1280,1440,1920]
def post(path, body):
    r=urllib.request.Request(B+path, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}); return json.load(urllib.request.urlopen(r))
async def shoot(pg, name, w):
    await pg.screenshot(path=f"{OUT}/{name}-{w}.png")
async def main():
    # One room per phase, built through the API, then each viewed at every width.
    lobby=post("/api/rooms",{})["code"]; host=post(f"/api/rooms/{lobby}/join-sample",{"name":"Caleb"}); post(f"/api/rooms/{lobby}/bots",host)
    game=post("/api/rooms",{})["code"]; gh=post(f"/api/rooms/{game}/join-sample",{"name":"Caleb"}); post(f"/api/rooms/{game}/bots",gh); post(f"/api/rooms/{game}/start",gh)
    rev=post("/api/rooms",{})["code"]; rh=post(f"/api/rooms/{rev}/join-sample",{"name":"Caleb"}); post(f"/api/rooms/{rev}/bots",rh); post(f"/api/rooms/{rev}/start",rh); post(f"/api/rooms/{rev}/next",rh)
    rep=post("/api/rooms",{})["code"]; ph=post(f"/api/rooms/{rep}/join-sample",{"name":"Caleb"}); post(f"/api/rooms/{rep}/bots",ph); post(f"/api/rooms/{rep}/start",ph)
    for _ in range(30):
        st=post(f"/api/rooms/{rep}/next",ph)
        if st["phase"]=="report": break
    empty=post("/api/rooms",{})["code"]
    async with async_playwright() as p:
        br=await p.chromium.launch(headless=True, channel="chrome")
        for w in WIDTHS:
            ctx=await br.new_context(viewport={"width":w,"height":900 if w>=768 else 844}, device_scale_factor=1)
            pg=await ctx.new_page()
            await pg.goto(B); await pg.wait_for_timeout(700); await shoot(pg,"a-home",w)
            await pg.goto(f"{B}/room/{empty}"); await pg.wait_for_timeout(900); await shoot(pg,"b-join",w)
            await pg.get_by_role("button", name="Connect Spotify").click(); await pg.wait_for_timeout(300); await shoot(pg,"b2-join-nudge",w)
            await pg.fill("input[placeholder='YOUR NAME']", "Caleb"); await pg.get_by_role("button", name="Connect Spotify").click(); await pg.wait_for_timeout(300); await shoot(pg,"c-join-statsfm",w)
            await pg.goto(f"{B}/room/{empty}?spotify=not_registered&name=Maia"); await pg.wait_for_timeout(800); await shoot(pg,"d-join-blocked",w)
            for code,cr,name,ms in [(lobby,host,"e-lobby",900),(game,gh,"f-question",1200),(rev,rh,"g-reveal",1200),(rep,ph,"h-report",1500)]:
                await pg.evaluate(f"localStorage.setItem('soundcheck:{code}', JSON.stringify({json.dumps(cr)}))")
                await pg.goto(f"{B}/room/{code}"); await pg.wait_for_timeout(ms); await shoot(pg,name,w)
            await pg.goto(f"{B}/privacy"); await pg.wait_for_timeout(500); await shoot(pg,"i-privacy",w)
            await pg.goto(f"{B}/room/ZZZZ"); await pg.wait_for_timeout(800); await shoot(pg,"j-missing",w)
            sw=await pg.evaluate("document.documentElement.scrollWidth"); 
            if sw>w: print("H-SCROLL", w)
            await ctx.close()
        await br.close()
asyncio.run(main())
