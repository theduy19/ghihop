"""Kiểm thử trang Tóm tắt cuộc họp: chế độ soát lỗi, che số nhạy cảm (kể cả số đọc bằng chữ) và điền lại.
Cách chạy: python3 KiemThu_SoatLoi.py <thư_mục_kết_quả> <đường_dẫn_trang.html> <đường_dẫn_jszip.min.js>
(jszip.min.js: npm i jszip@3.10.1 → node_modules/jszip/dist/jszip.min.js). Thoát mã 0 = đạt."""
import asyncio, sys
from playwright.async_api import async_playwright
OUT, PAGE, JSZIP = sys.argv[1], sys.argv[2], sys.argv[3]
fails = []
def check(ok, msg):
    print(('ĐẠT  ' if ok else 'TRƯỢT ') + msg)
    if not ok: fails.append(msg)
SOAT = """GHIHOP-SOAT v1
Tiêu đề: Gặp KH
Hình thức: Gặp khách hàng tại chi nhánh ngân hàng
Người nói: A = Tôi; B = Khách hàng
Từ điển riêng: Shinhan
---
#1 [09:00:01] A: em gọi lại số 0912 345 678 nhé
#2 [09:00:05] B: khoản vay đáo hạng tháng sau (máy nghe chưa rõ)
#3 [09:00:09] A: lãi suất 7 phẩy 5
#4 [09:00:12] B: Không chín một hai, ba bốn năm, sáu bảy tám
#5 [09:00:15] B: thời hạn hai mươi năm"""
STUB = """window.claude={use:async n=>n==='sample'?Object.assign(async(input,o)=>{window.__last=input;const m=input.match(/\\[SĐT-\\d+\\]/g)||[];o&&o.onText&&o.onText({text:'..'});return {text:JSON.stringify({sua:[{so:1,moi:'Em gọi lại số '+(m[1]||m[0]||'?')+' nhé.',ly_do:'thêm dấu câu',muc_do:'chắc'},{so:2,moi:'Khoản vay đáo hạn tháng sau.',ly_do:'đáo hạng → đáo hạn',muc_do:'chắc'},{so:3,moi:'Lãi suất 7 phẩy 5',ly_do:'không rõ con số',muc_do:'cần nghe lại'}],ghi_chu:'Khá.'})}},{}):null};"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await (await b.new_context(viewport={'width':390,'height':844})).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('https://cdnjs.cloudflare.com/**', lambda r: r.fulfill(path=JSZIP, content_type='application/javascript'))
        html = open(PAGE, encoding='utf-8').read()
        await pg.set_content('<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><script>' + STUB + '</script></head><body>' + html + '</body></html>')
        await pg.wait_for_timeout(500)
        await pg.fill('#src', SOAT); await pg.dispatch_event('#src', 'input')
        check(await pg.is_visible('#soatGo'), 'nhận ra bản cần soát, hiện nút Soát lỗi')
        await pg.click('#soatGo'); await pg.wait_for_timeout(500)
        sent = await pg.evaluate('window.__last') or ''
        check('0912' not in sent and 'Không chín một hai' not in sent, 'không gửi số điện thoại (dạng số và dạng chữ) cho Claude')
        check('hai mươi năm' in sent, 'không che nhầm cụm "hai mươi năm"')
        sua = await pg.evaluate('soat.sua')
        check('0912 345 678' in sua[0]['moi'] or 'Không chín' in sua[0]['moi'], 'kết quả trả về được điền lại số thật trên máy')
        await pg.click('#applyFix'); await pg.wait_for_timeout(200)
        src = await pg.input_value('#src')
        check('#2 [09:00:05] B: Khoản vay đáo hạn tháng sau.' in src, 'áp dụng bản sửa vào biên bản')
        check(not errs, 'không có lỗi JavaScript' + (': ' + '; '.join(errs) if errs else ''))
        await pg.screenshot(path=OUT + '/kiemthu_soatloi.png', full_page=True)
        await b.close()
asyncio.run(main())
print('KẾT QUẢ:', 'ĐẠT' if not fails else f'TRƯỢT {len(fails)} mục')
sys.exit(1 if fails else 0)
