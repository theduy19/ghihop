"""Kiểm thử hồi quy app Ghi Họp (trình duyệt Chromium không giao diện, micro giả lập).
Cách chạy: python3 KiemThu_GhiAm_MP3.py <thư_mục_kết_quả> <đường_dẫn_index.html> <đường_dẫn_lame.min.js>
(lame.min.js: npm i lamejs@1.2.1 → node_modules/lamejs/lame.min.js)
Thoát mã 0 = đạt, 1 = trượt."""
import asyncio, base64, sys, subprocess, json
from playwright.async_api import async_playwright
OUT, APP, LAME = sys.argv[1], sys.argv[2], sys.argv[3]
fails = []
def check(ok, msg):
    print(('ĐẠT  ' if ok else 'TRƯỢT ') + msg)
    if not ok: fails.append(msg)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required'])
        ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, permissions=['microphone'])
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('https://cdn.jsdelivr.net/npm/lamejs@1.2.1/lame.min.js', lambda r: r.fulfill(path=LAME, content_type='application/javascript'))
        await pg.goto('file://' + APP); await pg.wait_for_timeout(800)
        await pg.click('#btnRec'); await pg.wait_for_timeout(5000)
        await pg.evaluate("()=>{const t=Date.now(); addSeg(t-3500,t-1500,'xin hàn bank chào anh chị',0.4); addSeg(t-1400,t-200,'hôm nay mình bàn chỉ tiêu huy động');}")
        await pg.click('#btnRec'); await pg.wait_for_timeout(1500)   # tạm dừng
        await pg.click('#btnRec'); await pg.wait_for_timeout(3500)   # ghi tiếp
        await pg.evaluate("()=>{const t=Date.now(); addSeg(t-2500,t-500,'khách hàng đáo hạng 41 tỷ');}")
        await pg.click('#btnStop'); await pg.wait_for_timeout(2000)
        info = await pg.evaluate("()=>({codec:S.codec, sec:S.audioSamples/16000, gaps:S.gaps.length, segs:S.segs.map(s=>({t:s.text,o:s.orig||'',a0:s.a0,a1:s.a1,low:s.low||0}))})")
        check(info['codec'] == 'mp3', 'ghi bằng MP3')
        check(info['gaps'] == 1, 'tạm dừng được ghi thành 1 khoảng gián đoạn')
        check(info['segs'][0]['t'].startswith('Shinhan') and info['segs'][0]['o'], 'từ điển sửa "xin hàn" → "Shinhan" và giữ bản gốc')
        check(info['segs'][0]['low'] == 0.4, 'câu nghe chưa chắc được gắn nhãn')
        check(all(isinstance(s['a0'], (int, float)) for s in info['segs']), 'mỗi câu có mốc thời gian trong file ghi âm')
        b64 = await pg.evaluate("async()=>{const bl=await buildMp3(S);const u=new Uint8Array(await bl.arrayBuffer());let s='';for(const x of u)s+=String.fromCharCode(x);return btoa(s)}")
        open(OUT + '/kiemthu.mp3', 'wb').write(base64.b64decode(b64))
        pr = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,bit_rate:stream=sample_rate,channels,codec_name','-of','json', OUT + '/kiemthu.mp3'], capture_output=True, text=True)
        meta = json.loads(pr.stdout or '{}'); fmt = meta.get('format', {}); st = (meta.get('streams') or [{}])[0]
        dur = float(fmt.get('duration', 0))
        check(st.get('codec_name') == 'mp3' and st.get('sample_rate') == '16000' and st.get('channels') == 1, 'file MP3 16 kHz mono hợp lệ')
        check(abs(dur - info['sec']) < 0.6, f'thời lượng file ({dur:.2f}s) khớp thời gian ghi, không tính lúc tạm dừng ({info["sec"]:.2f}s)')
        await pg.evaluate("()=>playSeg(S.segs[2])"); await pg.wait_for_timeout(1200)
        pl = await pg.evaluate("()=>[playing!==null, player.currentTime, S.segs[2].a0]")
        check(pl[0] and abs(pl[1] - max(0, pl[2] - 3)) < 2.0, f'nút ▶ phát đúng đoạn (đang ở {pl[1]:.2f}s, câu bắt đầu {pl[2]:.2f}s)')
        msg = await pg.evaluate("""()=>{makeSoat(S); return applyFixes('GHIHOP-SUA v1\\n'+JSON.stringify({sua:[{so:3,moi:'Khách hàng đáo hạn 41 tỷ.',ly_do:'đáo hạng → đáo hạn',muc_do:'chắc'},{so:2,moi:'',ly_do:'không rõ con số',muc_do:'cần nghe lại'}]}))}""")
        fx = await pg.evaluate("()=>S.segs.map(s=>[s.fix||'',!!s.doubt])")
        check(fx[2][0] == 'claude' and fx[1][1], 'nhập kết quả soát lỗi: sửa đúng câu, gắn nhãn cần nghe lại')
        await pg.screenshot(path=OUT + '/kiemthu_app.png', full_page=True)
        check(not errs, 'không có lỗi JavaScript' + (': ' + '; '.join(errs) if errs else ''))
        await b.close()
asyncio.run(main())
print('KẾT QUẢ:', 'ĐẠT' if not fails else f'TRƯỢT {len(fails)} mục')
sys.exit(1 if fails else 0)
