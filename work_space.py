# -*- coding: utf-8 -*-
"""
WORK SPACE - 개인 업무 관리 프로그램 (Python + pywebview, 서버 불필요)

- 메인창 : 업무 참고 메모 / 미니 달력 / 3일 TO-DO / 진행 / 전체 조회 / 업무 달력 / 통계
- 미니창 : 오늘 현황 / 처리할 업무 / 3일 TO-DO (항상 위 고정 가능)
- 데이터 : exe(또는 .py)와 같은 폴더의 workspace_data.json 에 자동 저장
- 화면은 Windows 내장 웹뷰(WebView2)로 그려집니다.
"""
import json
import os
import shutil
import sys
import threading

import webview

APP_TITLE = "WORK SPACE"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_PATH = os.path.join(app_dir(), "workspace_data.json")


def holiday_map():
    """한국 공휴일(대체공휴일 포함) {YYYY-MM-DD: 이름}. 라이브러리가 없으면 빈 값(화면에서 고정 공휴일만 사용)."""
    out = {}
    try:
        import holidays
        kr = holidays.country_holidays("KR", years=range(2020, 2037))
        for d, name in kr.items():
            out[d.isoformat()] = str(name).split(",")[0].strip()
    except Exception:
        pass
    return out


HOLIDAYS = holiday_map()

CSS = r''':root{
  --bg:#f2f1f6; --panel:#ffffff; --line:#e6e3ee; --line2:#efedf5;
  --text:#4a4a5e; --muted:#8c8aa3; --faint:#b9b7c9;
  --accent:#8fa3e0; --accent-soft:#e7ecfb; --accent-ink:#4658ad;
  --lav:#e9e3f7; --lav-ink:#6a58a8;
  --mint:#e3f2ea; --mint-ink:#4c8a6b; --mint-fill:#a9d4bd;
  --butter:#fcf2d2; --butter-ink:#957616;
  --pink:#e2468a; --pink-soft:#ffe0ee; --pink-ink:#b3125e;
  --shadow:0 4px 18px rgba(80,72,120,.07);
  --font:"Pretendard Variable","Pretendard","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.45;overflow:hidden;
  -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer;border:1px solid var(--line);background:#fff;border-radius:10px}
input,textarea,select{border:1px solid var(--line);border-radius:10px;background:#fff;outline:none}
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(143,163,224,.2)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
#root{height:100%}
.hidden{display:none!important}

/* ── 레이아웃 ── */
.app{height:100%;display:flex;flex-direction:column;gap:12px;padding:14px 16px 16px}
.topbar{flex:none;height:56px;background:var(--panel);border:1px solid var(--line);border-radius:18px;display:flex;
  align-items:center;justify-content:space-between;padding:0 18px;box-shadow:var(--shadow)}
.brand{font-size:19px;font-weight:700;letter-spacing:.4px;color:#5d6aa6}
.brand span{font-size:12px;color:var(--muted);font-weight:500;margin-left:8px;letter-spacing:0}
.top-actions{display:flex;gap:10px;align-items:center}
.today-text{color:var(--muted);font-size:13px}
.btn{padding:7px 14px;background:#f7f6fb;color:var(--text);font-weight:600;font-size:13px}
.btn:hover{background:#eeedf7}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:#7e93d6}
.btn.danger{background:var(--pink-soft);border-color:#f7bcd7;color:var(--pink-ink)}
.note-card{flex:none;background:#fff8e1;border:1px solid #f3e6b8;border-radius:18px;padding:10px 14px 8px;box-shadow:var(--shadow)}
.note-title{font-size:12px;font-weight:700;color:#9a8230;margin-bottom:4px}
.note-card textarea{width:100%;height:58px;resize:vertical;border:0;background:transparent;padding:2px 0;color:#6b5f3a;line-height:1.6;box-shadow:none}
.layout{flex:1;min-height:0;display:grid;grid-template-columns:292px 1fr;gap:12px}
.sidebar{min-height:0;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}
.main{min-height:0;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);padding:16px 18px 18px}

/* ── 좌측 미니 달력 ── */
.side-cal{flex:none;padding:14px 14px 10px;border-bottom:1px solid var(--line2)}
.mini-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.mini-head .ttl{font-weight:700;font-size:15px}
.mini-head button{width:28px;height:28px;border:0;background:transparent;font-size:20px;line-height:1;color:var(--muted);border-radius:8px;padding:0}
.mini-head button:hover{background:var(--accent-soft);color:var(--accent-ink)}
.mini-head .today-btn{width:auto;padding:0 8px;font-size:11px;font-weight:600;border:1px solid var(--line);background:#fff;height:24px}
.wk{display:grid;grid-template-columns:repeat(7,1fr);text-align:center;font-size:11px;color:var(--muted);margin-bottom:2px}
.wk span:first-child{color:#d77f9f}.wk span:last-child{color:#7f94c4}
.cal7{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.day{position:relative;height:34px;border-radius:10px;display:flex;align-items:flex-start;justify-content:center;padding-top:6px;
  cursor:pointer;font-size:13px}
.day:hover{background:var(--accent-soft)}
.day.muted{color:#cbc9d8}
.day.sun{color:#d77f9f}.day.sat{color:#7f94c4}
.day.muted.sun,.day.muted.sat{color:#dcd9e6}
.day.today{background:var(--accent-soft);color:var(--accent-ink);font-weight:700;box-shadow:inset 0 0 0 1.5px #b9c6ee}
.day.has::after{content:"";position:absolute;bottom:4px;left:50%;width:5px;height:5px;margin-left:-2.5px;border-radius:50%;background:var(--accent)}
.day.has.late::after{background:var(--pink)}

/* ── TO-DO ── */
.side-todo{flex:1;min-height:0;display:flex;flex-direction:column;padding:12px 8px 8px 14px}
.side-title{font-weight:700;font-size:14px;margin:0 0 6px;padding-right:6px}
.todo-scroll{flex:1;min-height:0;overflow-y:auto;padding-right:6px}
.grp-t{font-size:12px;font-weight:700;color:#7d7b95;margin:12px 0 6px}
.grp-t:first-child{margin-top:2px}
.grp-t.late{color:var(--pink-ink)}
.quick{display:flex;gap:6px;margin-bottom:4px}
.quick input{flex:1;min-width:0;padding:8px 10px;font-size:13px}
.quick button{width:34px;background:var(--accent-soft);border-color:#d3dcf6;color:var(--accent-ink);font-weight:700}
.tr{display:flex;align-items:center;gap:8px;padding:7px 2px;border-bottom:1px solid var(--line2);font-size:13px}
.tr .tx{flex:1;min-width:0;word-break:break-all;line-height:1.4}
.tr.done .tx{text-decoration:line-through;color:var(--faint)}
.tr.late .tx{color:var(--pink-ink)}
.chk{flex:none;width:19px;height:19px;border-radius:7px;padding:0;border:1.5px solid #c7c5d8;background:#fff;color:#fff;font-size:12px;line-height:1;display:grid;place-items:center}
.chk.on{background:var(--mint-fill);border-color:var(--mint-fill)}
.tr .x{flex:none;border:0;background:transparent;color:#c5c3d6;padding:2px 5px;border-radius:6px;font-size:13px}
.tr .x:hover{background:var(--pink-soft);color:var(--pink-ink)}
.tr .mv:hover{background:var(--accent-soft);color:var(--accent-ink)}
.tempty{font-size:12px;color:#bdbbd0;padding:5px 2px}

/* ── 탭 ── */
.tabs{flex:none;display:flex;gap:6px;padding:4px;background:#f4f3f9;border-radius:14px;align-self:flex-start;margin-bottom:14px}
.tab{width:108px;height:36px;border:0;border-radius:11px;background:transparent;color:var(--muted);font-weight:600;font-size:14px;
  display:flex;align-items:center;justify-content:center;gap:6px;transition:background .15s,color .15s}
.tab:hover{background:#eceaf6;color:var(--text)}
.tab.active{background:var(--accent);color:#fff;box-shadow:0 2px 8px rgba(143,163,224,.45)}
.tab .cnt{min-width:20px;height:20px;padding:0 6px;border-radius:999px;background:rgba(255,255,255,.28);font-size:11px;display:inline-grid;place-items:center}
.tab:not(.active) .cnt{background:#e6e4f0;color:var(--muted)}
.panel{flex:1;min-height:0;overflow:auto;padding-right:2px;display:flex;flex-direction:column}
.sec-head{flex:none;display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;gap:12px}
.sec-head h2{margin:0;font-size:19px}
.sub{color:var(--muted);font-size:12px;margin-top:2px}
.nav{display:flex;align-items:center;gap:6px}
.nav .lbl{min-width:104px;text-align:center;font-weight:700}
.nav button{height:32px;min-width:32px;padding:0 10px;font-weight:600;background:#fff}
.nav button:hover{background:var(--accent-soft)}

/* ── 표(행) ── */
.table{border:1px solid var(--line);border-radius:14px;overflow:hidden;flex:none}
.rw{display:grid;align-items:center;gap:12px;padding:0 16px;min-height:52px;border-bottom:1px solid var(--line2)}
.rw:last-child{border-bottom:0}
.rw.prog{grid-template-columns:minmax(0,1fr) 160px 200px 170px}
.rw.all{grid-template-columns:minmax(0,1fr) 160px 200px 140px}
.rw.head{min-height:40px;background:#f6f5fa;color:#7d7b95;font-weight:600;font-size:12px}
.rw .c-t{font-weight:600;word-break:break-all}
.rw .c-p,.rw .c-m{color:#6f6d86;font-size:13px}
.rw .c-a{display:flex;justify-content:flex-end;align-items:center;gap:6px}
.rw.done .c-t{color:var(--faint);font-weight:500}
.rw.done .c-p,.rw.done .c-m{color:var(--faint)}
.rw.pink{background:var(--pink-soft);box-shadow:inset 4px 0 0 var(--pink)}
.rw.pink .c-t{color:var(--pink-ink)}
.rw.pink .c-p,.rw.pink .c-m{color:#c0457f}
.tag{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;margin-left:6px;vertical-align:1px}
.tag.pink{background:var(--pink);color:#fff}
.tag.amber{background:var(--butter);color:var(--butter-ink)}
.tag.adj{background:var(--lav);color:var(--lav-ink)}
.action,.undo,.badge{white-space:nowrap}
.badge{display:inline-flex;align-items:center;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:700}
.badge.run{background:var(--accent-soft);color:var(--accent-ink)}
.badge.done{background:var(--mint);color:var(--mint-ink)}
.action{padding:6px 14px;font-size:12px;font-weight:700;border-radius:999px}
.action.start{background:var(--accent);border-color:var(--accent);color:#fff}
.action.start:hover{background:#7e93d6}
.action.finish{background:var(--mint);border-color:#c5e3d3;color:var(--mint-ink)}
.action.finish:hover{background:#d3ecde}
.undo{border:0;background:transparent;color:#a3a1b9;font-size:12px;font-weight:600;padding:5px 7px;border-radius:8px;text-decoration:underline;text-underline-offset:2px}
.undo:hover{background:#f1f0f8;color:var(--text)}
.empty{flex:1;display:grid;place-items:center;color:#b9b7c9;text-align:center;padding:50px 10px;line-height:1.8}
.empty b{display:block;color:#a5a3bb;font-size:15px}

/* ── 업무 달력 ── */
.cal-wrap{flex:1;min-height:0;display:flex;flex-direction:column;border:1px solid var(--line);border-radius:14px;overflow:hidden;min-height:420px}
.cal-wk{flex:none;display:grid;grid-template-columns:repeat(7,1fr);background:#f6f5fa}
.cal-wk div{padding:8px;text-align:center;font-size:12px;font-weight:600;color:#7d7b95}
.cal-wk div:first-child{color:#d77f9f}.cal-wk div:last-child{color:#7f94c4}
.cal-grid{flex:1;display:flex;flex-direction:column;overflow:auto}
.week{position:relative;flex:1 0 auto;min-height:calc(40px + var(--n,0)*25px + 8px)}
.cells{position:absolute;inset:0;display:grid;grid-template-columns:repeat(7,1fr)}
.cell{border-top:1px solid var(--line2);border-right:1px solid var(--line2);padding:5px 7px;cursor:pointer;overflow:hidden}
.cell:nth-child(7n){border-right:0}
.cell:hover{background:#fafaff}
.cell.other{background:#fbfafd}
.cell.other .dn{color:#cbc9d8}
.cell.off{background:#fcfbfe}
.cell.today{background:#f3f6ff}
.dn{display:inline-grid;place-items:center;min-width:24px;height:24px;border-radius:999px;font-size:12px;font-weight:600;padding:0 4px}
.dn.red{color:#d77f9f}.dn.blue{color:#7f94c4}
.cell.today .dn{background:var(--accent);color:#fff}
.hn{float:right;font-size:11px;color:#d77f9f;max-width:62%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;margin-top:4px}
.bars{position:relative;display:grid;grid-template-columns:repeat(7,1fr);grid-auto-rows:22px;row-gap:3px;padding:33px 4px 0;pointer-events:none}
.bar{height:22px;line-height:22px;padding:0 9px;font-size:12px;font-weight:600;border-radius:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar.ready{background:#e8edf8;color:#5470a0}
.bar.doing{background:#b9c8f1;color:#2f4585}
.bar.done{background:var(--mint);color:#79a58d;text-decoration:line-through;font-weight:500}
.bar.pink{background:var(--pink);color:#fff}
.bar.todo{background:var(--butter);color:var(--butter-ink);font-weight:500}
.bar.cl{border-top-left-radius:0;border-bottom-left-radius:0;margin-left:-4px}
.bar.cr{border-top-right-radius:0;border-bottom-right-radius:0;margin-right:-4px}
.legend{display:flex;gap:14px;font-size:12px;color:var(--muted);align-items:center}
.legend i{display:inline-block;width:11px;height:11px;border-radius:4px;margin-right:5px;vertical-align:-1px}

/* ── 통계 ── */
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:18px}
.stat{border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:#fff;box-shadow:var(--shadow)}
.stat .label{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px}
.stat .label i{width:8px;height:8px;border-radius:50%;display:inline-block}
.stat .num{font-size:30px;font-weight:700;margin-top:6px}
.chartbox{border:1px solid var(--line);border-radius:16px;padding:18px 20px}
.chartbox .ct{display:flex;justify-content:space-between;align-items:baseline}
.chartbox .rate{font-size:12px;color:var(--muted)}
.brow{display:flex;align-items:center;gap:12px;margin:14px 0}
.brow .bl{width:44px;font-size:13px;color:var(--muted)}
.brow .bt{flex:1;height:14px;background:#f1f0f7;border-radius:999px;overflow:hidden}
.brow .bf{height:100%;border-radius:999px;min-width:0}
.brow b{width:34px;text-align:right}

/* ── 모달 ── */
.modal-bg{position:fixed;inset:0;background:rgba(70,64,100,.28);display:flex;align-items:center;justify-content:center;padding:20px;z-index:50}
.modal{width:min(520px,100%);max-height:calc(100vh - 40px);overflow:auto;background:#fff;border-radius:20px;padding:22px;box-shadow:0 24px 70px rgba(50,45,90,.25)}
.modal h3{margin:0 0 14px;font-size:17px}
.modal h3 .hol{font-size:12px;font-weight:600;color:#d77f9f;margin-left:6px}
.form{display:grid;gap:8px}
.form label{font-size:12px;color:var(--muted);font-weight:600;margin-top:4px}
.form input{width:100%;padding:9px 11px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.form .hint{font-size:12px;color:var(--muted);background:#f7f6fb;border-radius:10px;padding:8px 10px;line-height:1.6}
.form .chkline{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text);font-weight:500;margin-top:2px}
.form .chkline input{width:auto}
.seg{display:flex;gap:4px;background:#f4f3f9;padding:4px;border-radius:12px}
.seg button{flex:1;border:0;background:transparent;border-radius:9px;padding:7px 4px;font-size:13px;font-weight:600;color:var(--muted)}
.seg button.on{background:var(--accent);color:#fff}
.err{color:var(--pink-ink);font-size:12px;min-height:18px;margin-top:6px}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.mlist{display:grid;gap:6px;margin:4px 0 12px}
.mitem{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line2);border-radius:12px;background:#fcfcff}
.mitem .mt{flex:1;min-width:0}
.mitem .mt b{display:block;font-size:13px;word-break:break-all}
.mitem .mt span{font-size:12px;color:var(--muted)}
.mitem .btn{padding:5px 10px;font-size:12px}
.mitem.pinkrow{background:var(--pink-soft);border-color:#f7c3dc}
.hint2{font-size:12px;color:var(--muted);margin:0 0 10px;line-height:1.6}

/* ── 미니창 ── */
.mini-app{height:100%;display:flex;flex-direction:column;gap:10px;padding:12px}
.mini-top{flex:none;display:flex;align-items:center;justify-content:space-between;padding:2px 4px}
.brand.sm{font-size:16px}
.pinbtn{padding:5px 11px;font-size:12px;font-weight:600;color:var(--muted);border-radius:999px;background:#fff}
.pinbtn.on{background:var(--accent-soft);color:var(--accent-ink);border-color:#cfd9f6}
.mini-card{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:12px 12px 10px}
.mini-card .mt{font-size:13px;font-weight:700;margin-bottom:8px}
.pills{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.pill{border-radius:12px;padding:8px 6px;text-align:center;background:#f6f5fb}
.pill b{display:block;font-size:20px;line-height:1.2}
.pill span{font-size:11px;color:var(--muted)}
.pill.p-pink{background:var(--pink-soft)}.pill.p-pink b{color:var(--pink-ink)}
.pill.p-blue{background:var(--accent-soft)}.pill.p-blue b{color:var(--accent-ink)}
.mini-tasks{flex:none;max-height:36%;display:flex;flex-direction:column;min-height:90px}
.mini-tasks .body{overflow-y:auto}
.mt-row{display:flex;align-items:center;gap:8px;padding:8px 8px;border-radius:11px;margin-bottom:4px;background:#f8f8fc;font-size:13px}
.mt-row .t{flex:1;min-width:0;font-weight:600;line-height:1.35;word-break:break-all}
.mt-row .t small{display:block;font-weight:500;color:var(--muted);font-size:11px}
.mt-row.pink{background:var(--pink-soft);box-shadow:inset 3px 0 0 var(--pink)}
.mt-row.pink .t{color:var(--pink-ink)}
.mt-row .action{padding:5px 11px;flex:none}
.mini-todo{flex:1;min-height:0;padding:0;display:flex;overflow:hidden}
.mini-todo .side-todo{padding:12px 6px 8px 12px;width:100%}

/* 근무일지 */
.logbox{flex:1;min-height:260px;width:100%;resize:none;padding:18px 20px;border-radius:14px;background:#fbfbfe;line-height:1.95;font-size:14px;cursor:text}
'''
LOGIC_JS = r'''/* WORK SPACE - 날짜/공휴일/반복 업무 계산 (화면과 무관한 순수 로직) */
const WSLogic = (function () {
  'use strict';
  const ctx = {
    S: { tasks: [], todos: [], prog: {}, extra_off: [] },
    HOL: {}, hasHol: false,
    nowFn: () => new Date(),
  };
  const WD = '일월화수목금토';
  const FIXED = { '01-01': '신정', '03-01': '삼일절', '05-05': '어린이날', '06-06': '현충일',
    '08-15': '광복절', '10-03': '개천절', '10-09': '한글날', '12-25': '성탄절' };

  const pad = n => String(n).padStart(2, '0');
  const D = (y, m, d) => new Date(y, m - 1, d, 12);
  const iso = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  const P = s => {
    if (!s) return null;
    const a = String(s).split('-').map(Number);
    if (a.length !== 3 || a.some(isNaN)) return null;
    return D(a[0], a[1], a[2]);
  };
  const addDays = (d, n) => { const x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; };
  const mlen = (y, m) => new Date(y, m, 0).getDate();
  const shiftMonth = (y, m, k) => { const t = y * 12 + (m - 1) + k; return [Math.floor(t / 12), t % 12 + 1]; };
  const today = () => { const n = ctx.nowFn(); return D(n.getFullYear(), n.getMonth() + 1, n.getDate()); };
  const diffDays = (a, b) => Math.round((a.getTime() - b.getTime()) / 864e5);
  const fmtMD = d => (d.getMonth() + 1) + '/' + d.getDate() + '(' + WD[d.getDay()] + ')';
  const same = (a, b) => iso(a) === iso(b);

  function setHol(h) { ctx.HOL = h || {}; ctx.hasHol = Object.keys(ctx.HOL).length > 0; }

  function holName(d) {
    const k = iso(d);
    const ex = (ctx.S.extra_off || []).find(x => x.date === k);
    if (ex) return ex.name || '휴일';
    if (ctx.hasHol) return ctx.HOL[k] || '';
    return FIXED[k.slice(5)] || '';
  }
  const isOff = d => d.getDay() === 0 || d.getDay() === 6 || !!holName(d);
  function prevWork(d) {
    let x = d;
    for (let i = 0; i < 40 && isOff(x); i++) x = addDays(x, -1);
    return x;
  }

  /* 반복 업무: y년 m월의 발생 (시작, 종료, 조정 여부) */
  function ruleOcc(t, y, m) {
    const ml = mlen(y, m);
    const a = parseInt(t.a, 10) || 0, b = parseInt(t.b, 10) || 0;
    if (t.type === 'monthly') {
      const n = D(y, m, Math.min(Math.max(a, 1), ml));
      const d = prevWork(n);
      return { s: d, e: d, adj: !same(n, d) };
    }
    if (t.type === 'eom') {
      let d = prevWork(D(y, m, ml));
      for (let i = 0; i < Math.max(a, 0); i++) d = prevWork(addDays(d, -1));
      return { s: d, e: d, adj: false };
    }
    if (t.type === 'period') {
      let s = D(y, m, Math.min(Math.max(a, 1), ml));
      let ey = y, em = m;
      if (b < a) [ey, em] = shiftMonth(y, m, 1);
      const e0 = D(ey, em, Math.min(Math.max(b, 1), mlen(ey, em)));
      const e = prevWork(e0);
      if (e < s) s = e;
      return { s, e, adj: !same(e0, e) };
    }
    return null;
  }

  /* 일회성 업무: 마감일이 휴일이면 직전 평일 */
  function onceSpan(t) {
    const s0 = P(t.start), e0 = P(t.end);
    if (!s0 && !e0) return null;
    let e = e0 || s0, adj = false;
    if (e0 && t.adjust !== false) {
      const pe = prevWork(e0);
      if (!same(pe, e0)) { e = pe; adj = true; }
    }
    let s = s0 || e;
    if (s > e) s = e;
    return { s, e, adj };
  }

  function mkOcc(t, key, s, e, adj) {
    return { key, id: t.id, kind: 'task', task: t, title: (t.time ? t.time + ' ' : '') + t.title, start: s, end: e, adj: !!adj };
  }

  function occRange(d1, d2, opt) {
    const out = [];
    for (const t of ctx.S.tasks) {
      if (t.type === 'once') {
        const sp = onceSpan(t);
        if (!sp || sp.e < d1 || sp.s > d2) continue;
        out.push(mkOcc(t, 't' + t.id, sp.s, sp.e, sp.adj));
      } else {
        let [y, m] = shiftMonth(d1.getFullYear(), d1.getMonth() + 1, -1);
        const end = d2.getFullYear() * 12 + d2.getMonth() + 1;
        while (y * 12 + m <= end) {
          const o = ruleOcc(t, y, m);
          if (o && !(o.e < d1 || o.s > d2)) out.push(mkOcc(t, 't' + t.id + '@' + y + '-' + pad(m), o.s, o.e, o.adj));
          [y, m] = shiftMonth(y, m, 1);
        }
      }
    }
    if (!(opt && opt.noTodos)) {
      for (const t of ctx.S.todos) {
        const d = P(t.date);
        if (d && !t.done && d >= d1 && d <= d2) out.push({ key: 'd' + t.id, id: t.id, kind: 'todo', title: t.text, start: d, end: d, todo: t });
      }
    }
    return out;
  }

  function occByKey(key) {
    const m = /^t(\d+)(?:@(\d{4})-(\d{2}))?$/.exec(key);
    if (!m) return null;
    const t = ctx.S.tasks.find(x => String(x.id) === m[1]);
    if (!t) return null;
    if (t.type === 'once') {
      const sp = onceSpan(t);
      return sp ? mkOcc(t, key, sp.s, sp.e, sp.adj) : null;
    }
    if (!m[2]) return null;
    const o = ruleOcc(t, +m[2], +m[3]);
    return o ? mkOcc(t, key, o.s, o.e, o.adj) : null;
  }

  const stOf = key => (ctx.S.prog[key] || {}).s || 'todo';
  function pinkOf(o) {
    if (o.kind !== 'task' || stOf(o.key) === 'done') return null;
    const t = iso(today()), e = iso(o.end);
    return e === t ? 'today' : e < t ? 'late' : null;
  }

  const byEnd = (a, b) => (a.end - b.end) || (a.start - b.start) || a.title.localeCompare(b.title, 'ko');
  function doingList() {
    const out = [];
    for (const k of Object.keys(ctx.S.prog)) {
      if (ctx.S.prog[k].s !== 'doing') continue;
      const o = occByKey(k);
      if (o) out.push(o);
    }
    return out.sort(byEnd);
  }
  function lateList() {
    const t = today();
    return occRange(addDays(t, -7), addDays(t, -1), { noTodos: true })
      .filter(o => o.end < t && stOf(o.key) !== 'done').sort(byEnd);
  }

  function startTask(key) { ctx.S.prog[key] = { s: 'doing', at: iso(today()) }; }
  function finishTask(key) { const p = ctx.S.prog[key] || {}; ctx.S.prog[key] = { s: 'done', at: p.at || iso(today()), done_at: iso(today()) }; }
  function resetTask(key) { delete ctx.S.prog[key]; }
  function removeTask(id) {
    ctx.S.tasks = ctx.S.tasks.filter(t => t.id !== id);
    for (const k of Object.keys(ctx.S.prog)) if (k === 't' + id || k.startsWith('t' + id + '@')) delete ctx.S.prog[k];
  }

  function describeTask(t) {
    if (t.type === 'monthly') return '매월 ' + t.a + '일 (휴일이면 직전 평일)';
    if (t.type === 'eom') return parseInt(t.a, 10) === 0 ? '월말 마지막 영업일' : '월말 마지막 영업일 기준 ' + t.a + '영업일 전';
    if (t.type === 'period') return '매월 ' + t.a + '일 ~ ' + t.b + '일 (종료일이 휴일이면 직전 평일)';
    const s = P(t.start), e = P(t.end);
    if (s && e && !same(s, e)) return iso(s) + ' ~ ' + iso(e);
    return iso(e || s);
  }

  /* 예전(tkinter) 버전 데이터 / 빈 데이터 정리 */
  function migrate(s) {
    s = s || {};
    s.memo = s.memo || '';
    s.todos = s.todos || [];
    s.tasks = s.tasks || [];
    s.prog = s.prog || {};
    s.extra_off = s.extra_off || [];
    s.next_id = s.next_id || 1;
    if (s.rules) {
      for (const r of s.rules) s.tasks.push({ id: r.id, title: r.title, type: r.type, a: r.a, b: r.b, time: r.time || '', start: '', end: '', adjust: true });
      delete s.rules;
    }
    if (s.cases) {
      for (const c of s.cases) {
        s.tasks.push({ id: c.id, title: [c.company, c.title].filter(Boolean).join(' · ') || '업무', type: 'once', a: 0, b: 0, time: '', start: c.start || '', end: c.due || '', adjust: c.adjust !== false });
        if (c.done) s.prog['t' + c.id] = { s: 'done', done_at: c.done_at || '' };
      }
      delete s.cases;
    }
    delete s.notepad; delete s.cats; delete s.geo;
    return s;
  }

  function setState(s) { ctx.S = s; }

  return { ctx, WD, pad, D, iso, P, addDays, mlen, shiftMonth, today, diffDays, fmtMD, same, setHol, holName, isOff, prevWork,
    ruleOcc, onceSpan, occRange, occByKey, stOf, pinkOf, byEnd, doingList, lateList, startTask, finishTask, resetTask,
    removeTask, describeTask, migrate, setState };
})();
if (typeof module !== 'undefined') module.exports = WSLogic;
'''
APP_JS = r'''/* WORK SPACE - 화면 (메인창 / 미니창 공용) */
(function () {
  'use strict';
  const L = WSLogic;
  const { iso, P, D, addDays, mlen, shiftMonth, today, holName, fmtMD, diffDays, stOf } = L;
  const MODE = window.WS_MODE || 'main';
  const WD = L.WD;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const $ = (s, r) => (r || document).querySelector(s);

  let S = null, curModal = null, form = null, pinned = true, lastDay = '';
  const t0 = today();
  const ui = { tab: 'prog', calY: t0.getFullYear(), calM: t0.getMonth() + 1, listY: t0.getFullYear(), listM: t0.getMonth() + 1,
    statY: t0.getFullYear(), statM: t0.getMonth() + 1, logDate: '', miniY: t0.getFullYear(), miniM: t0.getMonth() + 1 };

  /* ── 저장 / 불러오기 ── */
  const hasPy = () => !!(window.pywebview && window.pywebview.api && window.pywebview.api.load_state);
  async function loadAll() {
    if (hasPy()) return await window.pywebview.api.load_state();
    let st = {};
    try { st = JSON.parse(localStorage.getItem('ws_state') || '{}'); } catch (e) { /* ignore */ }
    return { state: st, holidays: {} };
  }
  function persist() {
    try {
      if (hasPy()) window.pywebview.api.save_state(S, MODE);
      else localStorage.setItem('ws_state', JSON.stringify(S));
    } catch (e) { /* ignore */ }
  }
  function commit() { persist(); render(); }

  /* ── 공통 헬퍼 ── */
  function monthWeeks(y, m) {
    const first = D(y, m, 1), last = D(y, m, mlen(y, m));
    let s = addDays(first, -first.getDay());
    const weeks = [];
    while (s <= last) { weeks.push(Array.from({ length: 7 }, (_, i) => addDays(s, i))); s = addDays(s, 7); }
    return weeks;
  }
  const periodText = o => (iso(o.start) === iso(o.end) ? fmtMD(o.end) : fmtMD(o.start) + ' ~ ' + fmtMD(o.end));
  function dueCell(o) {
    let h = fmtMD(o.end);
    if (o.adj) h += '<span class="tag adj" title="주말·공휴일이라 직전 평일로 조정됐어요">조정</span>';
    const pk = L.pinkOf(o);
    const n = diffDays(o.end, today());
    if (pk === 'today') h += '<span class="tag pink">오늘 마감</span>';
    else if (pk === 'late') h += '<span class="tag pink">지연 D+' + (-n) + '</span>';
    else if (stOf(o.key) !== 'done' && n >= 1 && n <= 3) h += '<span class="tag amber">D-' + n + '</span>';
    return h;
  }

  /* ── 모달 ── */
  function closeModal() {
    const b = document.querySelector('.modal-bg');
    if (b) b.remove();
    curModal = null; form = null;
  }
  function openModal(builder, refreshable) {
    closeModal();
    const back = document.createElement('div');
    back.className = 'modal-bg';
    back.innerHTML = '<div class="modal"></div>';
    document.body.appendChild(back);
    const el = back.firstChild;
    el.innerHTML = builder();
    back.addEventListener('mousedown', e => { if (e.target === back) closeModal(); });
    curModal = { el, refresh: refreshable ? () => { el.innerHTML = builder(); } : null };
    return curModal;
  }
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  function confirmBox(msg, yesLabel, onYes, onNo) {
    openModal(() => '<h3>확인</h3><p style="margin:0 0 4px;line-height:1.7">' + esc(msg) + '</p>' +
      '<div class="modal-actions"><button class="btn" data-act="mNo">취소</button><button class="btn danger" data-act="mYes">' + esc(yesLabel) + '</button></div>');
    confirmBox.yes = onYes; confirmBox.no = onNo;
  }

  /* 날짜 상세 */
  function openDay(ds) {
    const d = P(ds);
    openModal(() => {
      const items = L.occRange(d, d);
      const tasks = items.filter(o => o.kind === 'task').sort(L.byEnd);
      const todos = items.filter(o => o.kind === 'todo');
      const hn = holName(d);
      let h = '<h3>' + d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일 (' + WD[d.getDay()] + ')' +
        (hn ? '<span class="hol">' + esc(hn) + '</span>' : '') + '</h3><div class="mlist">';
      if (!tasks.length && !todos.length) h += '<div class="tempty">등록된 일정이 없어요</div>';
      for (const o of tasks) {
        const pk = L.pinkOf(o);
        h += '<div class="mitem ' + (pk ? 'pinkrow' : '') + '"><div class="mt"><b>' + esc(o.title) + '</b><span>' + periodText(o) +
          (o.task.type !== 'once' ? ' · 매월 반복' : '') + '</span></div>' + stateCell(o, true) +
          '<button class="btn" data-act="editTask" data-id="' + o.id + '">수정</button></div>';
      }
      for (const o of todos) {
        h += '<div class="mitem"><div class="mt"><b>' + esc(o.title) + '</b><span>할 일</span></div>' +
          '<button class="btn" data-act="tdDel" data-id="' + o.id + '">삭제</button></div>';
      }
      h += '</div><div class="quick"><input id="dayIn" placeholder="이 날짜에 할 일 추가"><button data-act="dayAdd" data-date="' + ds + '">＋</button></div>' +
        '<div class="modal-actions"><button class="btn primary" data-act="newTask" data-date="' + ds + '">＋ 이 날짜에 업무 등록</button>' +
        '<button class="btn" data-act="mClose">닫기</button></div>';
      return h;
    }, true);
    setTimeout(() => { const i = $('#dayIn'); if (i) i.addEventListener('keydown', e => { if (e.key === 'Enter') acts.dayAdd(i.nextElementSibling); }); }, 0);
  }

  /* 업무 등록 / 수정 */
  function openTask(task, preset) {
    const isNew = !task;
    const t = task ? JSON.parse(JSON.stringify(task)) :
      { id: 0, title: '', type: 'once', a: 25, b: 28, start: preset || '', end: preset || '', time: '', adjust: true };
    const TYPES = [['once', '이번만'], ['monthly', '매월 N일'], ['eom', '월말 기준'], ['period', '매월 기간']];
    const M = openModal(() => '<h3>' + (isNew ? '업무 등록' : '업무 수정') + '</h3><div class="form">' +
      '<label>업무명</label><input id="fTitle" value="' + esc(t.title) + '" placeholder="예: 월말 자료 정리">' +
      '<label>반복 방식</label><div class="seg" id="fType"></div><div id="fFields"></div>' +
      '<label>시간 (선택)</label><input id="fTime" type="time" value="' + esc(t.time || '') + '"></div>' +
      '<div class="err" id="fErr"></div><div class="modal-actions"><button class="btn" data-act="mClose">취소</button>' +
      '<button class="btn primary" data-act="fSave">저장</button></div>');
    const g = id => M.el.querySelector('#' + id);
    const read = () => {
      if (g('fTitle')) t.title = g('fTitle').value.trim();
      if (g('fTime')) t.time = g('fTime').value;
      if (g('fStart')) { t.start = g('fStart').value; t.end = g('fEnd').value; t.adjust = g('fAdj').checked; }
      if (g('fA')) { const v = parseInt(g('fA').value, 10); if (!isNaN(v)) t.a = v; }
      if (g('fB')) { const v = parseInt(g('fB').value, 10); if (!isNaN(v)) t.b = v; }
    };
    const paint = () => {
      g('fType').innerHTML = TYPES.map(([v, n]) => '<button type="button" class="' + (t.type === v ? 'on' : '') + '" data-act="fType" data-v="' + v + '">' + n + '</button>').join('');
      let h = '';
      if (t.type === 'once') {
        h = '<div class="form-row"><div><label>시작일</label><input id="fStart" type="date" value="' + esc(t.start || '') + '"></div>' +
          '<div><label>마감일</label><input id="fEnd" type="date" value="' + esc(t.end || '') + '"></div></div>' +
          '<label class="chkline"><input id="fAdj" type="checkbox" ' + (t.adjust !== false ? 'checked' : '') + '>마감일이 주말·공휴일이면 직전 평일로 자동 조정</label>' +
          '<div class="hint">하루짜리 업무는 시작일과 마감일을 같게 하거나 마감일만 넣으세요.</div>';
      } else if (t.type === 'monthly') {
        h = '<label>날짜 (일)</label><input id="fA" type="number" min="1" max="31" value="' + t.a + '">' +
          '<div class="hint">매월 N일이 주말·공휴일이면 직전 평일에 표시돼요.</div>';
      } else if (t.type === 'eom') {
        h = '<label>며칠 전 영업일</label><input id="fA" type="number" min="0" max="20" value="' + t.a + '">' +
          '<div class="hint">0 = 월말 마지막 영업일, 1 = 그 전 영업일.<br>말일이 휴일이면 앞 영업일을 기준으로 계산해요.</div>';
      } else {
        h = '<div class="form-row"><div><label>시작일 (일)</label><input id="fA" type="number" min="1" max="31" value="' + t.a + '"></div>' +
          '<div><label>종료일 (일)</label><input id="fB" type="number" min="1" max="31" value="' + t.b + '"></div></div>' +
          '<div class="hint">종료일이 주말·공휴일이면 직전 평일까지만 기간이 잡혀요.<br>종료일이 시작일보다 작으면 다음 달로 넘어가요.</div>';
      }
      g('fFields').innerHTML = h;
    };
    form = { t, isNew, read, paint, g };
    paint();
    setTimeout(() => { const i = g('fTitle'); if (i) i.focus(); }, 0);
  }

  function openManage() {
    openModal(() => {
      let h = '<h3>등록된 업무 관리</h3><p class="hint2">반복 업무를 지우면 모든 달에서 사라져요.</p><div class="mlist">';
      if (!S.tasks.length) h += '<div class="tempty">등록된 업무가 없어요</div>';
      for (const t of S.tasks.slice().sort((a, b) => a.title.localeCompare(b.title, 'ko'))) {
        h += '<div class="mitem"><div class="mt"><b>' + esc((t.time ? t.time + ' ' : '') + t.title) + '</b><span>' + esc(L.describeTask(t)) + '</span></div>' +
          '<button class="btn" data-act="editTask" data-id="' + t.id + '">수정</button>' +
          '<button class="btn danger" data-act="delTask" data-id="' + t.id + '">삭제</button></div>';
      }
      return h + '</div><div class="modal-actions"><button class="btn primary" data-act="newTask" data-date="">＋ 업무 등록</button><button class="btn" data-act="mClose">닫기</button></div>';
    }, true);
  }

  function openHolidays() {
    openModal(() => {
      let h = '<h3>휴일 추가</h3><p class="hint2">기본 공휴일(대체공휴일 포함)은 자동 반영돼요.<br>임시공휴일·회사 휴무일만 추가하세요.</p><div class="mlist">';
      const ex = (S.extra_off || []).slice().sort((a, b) => a.date.localeCompare(b.date));
      if (!ex.length) h += '<div class="tempty">추가한 휴일이 없어요</div>';
      for (const x of ex) {
        h += '<div class="mitem"><div class="mt"><b>' + esc(x.date) + '</b><span>' + esc(x.name || '휴일') + '</span></div>' +
          '<button class="btn danger" data-act="delHol" data-date="' + esc(x.date) + '">삭제</button></div>';
      }
      return h + '</div><div class="form-row"><input id="hDate" type="date"><input id="hName" placeholder="이름 (선택)"></div>' +
        '<div class="err" id="hErr"></div><div class="modal-actions"><button class="btn primary" data-act="addHol">추가</button><button class="btn" data-act="mClose">닫기</button></div>';
    }, true);
  }

  /* ── 상태 버튼 / 칩 ── */
  function stateCell(o, small) {
    const st = stOf(o.key), k = ' data-key="' + o.key + '"';
    if (st === 'todo') return '<button class="action start" data-act="start"' + k + '>진행</button>';
    if (st === 'doing') return '<span class="badge run">진행</span><button class="undo" data-act="reset"' + k + ' title="시작을 취소하고 시작 전으로 되돌려요">취소</button>';
    return '<span class="badge done">완료</span><button class="undo" data-act="reopen"' + k + ' title="완료를 취소하고 진행으로 되돌려요">취소</button>';
  }

  /* ── 동작 ── */
  const acts = {
    toggleMini() { if (hasPy()) window.pywebview.api.toggle_mini(); },
    pin(el) { pinned = !pinned; el.classList.toggle('on', pinned); if (hasPy()) window.pywebview.api.set_topmost(pinned); },
    tab(el) {
      ui.tab = el.dataset.tab; renderTabs(); renderPanel();
      if (ui.tab === 'log') focusLog();
    },
    logPrev() { ui.logDate = iso(addDays(P(ui.logDate || iso(today())), -1)); renderPanel(); focusLog(); },
    logNext() { const n = iso(addDays(P(ui.logDate || iso(today())), 1)); ui.logDate = n >= iso(today()) ? '' : n; renderPanel(); focusLog(); },
    logToday() { ui.logDate = ''; renderPanel(); focusLog(); },
    logCopy(el) {
      const ta = $('#logText'); if (!ta) return;
      const ok = () => { el.textContent = '복사됨 ✓'; setTimeout(() => { if (el.isConnected) el.textContent = '복사'; }, 1500); };
      const fallback = () => { ta.focus(); ta.select(); try { document.execCommand('copy'); ok(); } catch (e) { /* ignore */ } };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ta.value).then(ok, fallback);
      else fallback();
    },
    start(el) { L.startTask(el.dataset.key); commit(); },
    finish(el) { L.finishTask(el.dataset.key); commit(); },
    reset(el) { L.resetTask(el.dataset.key); commit(); },
    reopen(el) { const k = el.dataset.key, p = S.prog[k] || {}; S.prog[k] = { s: 'doing', at: p.at || iso(today()) }; commit(); },
    /* 월 이동 */
    calPrev() { [ui.calY, ui.calM] = shiftMonth(ui.calY, ui.calM, -1); renderPanel(); },
    calNext() { [ui.calY, ui.calM] = shiftMonth(ui.calY, ui.calM, 1); renderPanel(); },
    calToday() { const t = today(); ui.calY = t.getFullYear(); ui.calM = t.getMonth() + 1; renderPanel(); },
    listPrev() { [ui.listY, ui.listM] = shiftMonth(ui.listY, ui.listM, -1); renderPanel(); },
    listNext() { [ui.listY, ui.listM] = shiftMonth(ui.listY, ui.listM, 1); renderPanel(); },
    listToday() { const t = today(); ui.listY = t.getFullYear(); ui.listM = t.getMonth() + 1; renderPanel(); },
    statPrev() { [ui.statY, ui.statM] = shiftMonth(ui.statY, ui.statM, -1); renderPanel(); },
    statNext() { [ui.statY, ui.statM] = shiftMonth(ui.statY, ui.statM, 1); renderPanel(); },
    statToday() { const t = today(); ui.statY = t.getFullYear(); ui.statM = t.getMonth() + 1; renderPanel(); },
    miniPrev() { [ui.miniY, ui.miniM] = shiftMonth(ui.miniY, ui.miniM, -1); renderMiniCal(); },
    miniNext() { [ui.miniY, ui.miniM] = shiftMonth(ui.miniY, ui.miniM, 1); renderMiniCal(); },
    miniToday() { const t = today(); ui.miniY = t.getFullYear(); ui.miniM = t.getMonth() + 1; renderMiniCal(); },
    miniDay(el) {
      const d = P(el.dataset.date);
      ui.calY = d.getFullYear(); ui.calM = d.getMonth() + 1; ui.tab = 'cal';
      renderTabs(); renderPanel(); openDay(el.dataset.date);
    },
    day(el) { openDay(el.dataset.date); },
    /* 모달 */
    mClose() { closeModal(); },
    mYes() { const f = confirmBox.yes; closeModal(); if (f) f(); },
    mNo() { const f = confirmBox.no; closeModal(); if (f) f(); },
    newTask(el) { openTask(null, el.dataset.date || ''); },
    editTask(el) { const t = S.tasks.find(x => String(x.id) === el.dataset.id); if (t) openTask(t); },
    delTask(el) {
      const t = S.tasks.find(x => String(x.id) === el.dataset.id); if (!t) return;
      confirmBox('"' + t.title + '" 업무를 삭제할까요?' + (t.type !== 'once' ? '\n반복 업무는 모든 달에서 사라져요.' : ''), '삭제',
        () => { L.removeTask(t.id); commit(); openManage(); }, () => openManage());
    },
    manage() { openManage(); },
    addTask() { openTask(null, ''); },
    holidays() { openHolidays(); },
    addHol() {
      const d = $('#hDate').value; if (!d) { $('#hErr').textContent = '날짜를 선택해 주세요.'; return; }
      S.extra_off = (S.extra_off || []).filter(x => x.date !== d); S.extra_off.push({ date: d, name: $('#hName').value.trim() || '휴일' }); commit();
    },
    delHol(el) { S.extra_off = (S.extra_off || []).filter(x => x.date !== el.dataset.date); commit(); },
    fType(el) { form.read(); form.t.type = el.dataset.v; form.paint(); },
    fSave() {
      const { t, isNew } = form; form.read();
      const err = m => { form.g('fErr').textContent = m; };
      if (!t.title) return err('업무명을 입력해 주세요.');
      if (t.type === 'once' && !t.start && !t.end) return err('시작일이나 마감일을 선택해 주세요.');
      if ((t.type === 'monthly' || t.type === 'period') && !(t.a >= 1 && t.a <= 31)) return err('날짜는 1~31 사이로 입력해 주세요.');
      if (t.type === 'period' && !(t.b >= 1 && t.b <= 31)) return err('종료일은 1~31 사이로 입력해 주세요.');
      if (t.type === 'eom' && !(t.a >= 0 && t.a <= 20)) return err('0~20 사이로 입력해 주세요.');
      if (isNew) { t.id = S.next_id++; S.tasks.push(t); }
      else { const i = S.tasks.findIndex(x => x.id === t.id); if (i >= 0) S.tasks[i] = t; }
      closeModal(); commit();
    },
    /* TO-DO */
    addTodo(el) {
      const k = el.dataset.k, inp = $(k === 'today' ? '#tdTodayIn' : '#tdTomIn'), v = inp.value.trim(); if (!v) return;
      const d = addDays(today(), k === 'today' ? 0 : 1);
      S.todos.push({ id: S.next_id++, text: v, date: iso(d), done: false }); inp.value = ''; commit();
    },
    dayAdd(el) {
      const inp = $('#dayIn'), v = inp.value.trim(); if (!v) return;
      S.todos.push({ id: S.next_id++, text: v, date: el.dataset.date || curDayDate(), done: false }); commit();
    },
    tdToggle(el) { const t = S.todos.find(x => String(x.id) === el.dataset.id); if (t) { t.done = !t.done; commit(); } },
    tdDel(el) { S.todos = S.todos.filter(x => String(x.id) !== el.dataset.id); commit(); },
    tdPush(el) {
      const t = S.todos.find(x => String(x.id) === el.dataset.id); if (!t) return;
      const d = P(t.date) || today(), n = today(); t.date = iso(d < n ? n : addDays(d, 1)); commit();
    },
  };
  function curDayDate() { const b = $('[data-act="newTask"]'); return b ? b.dataset.date : iso(today()); }
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-act]');
    if (!el) return;
    const f = acts[el.dataset.act];
    if (f) { e.preventDefault(); f(el, e); }
  });

  /* ── 좌측: 미니 달력 ── */
  function renderMiniCal() {
    const host = $('#miniCal'); if (!host) return;
    const y = ui.miniY, m = ui.miniM, weeks = monthWeeks(y, m);
    const first = weeks[0][0], last = weeks[weeks.length - 1][6], t = today(), ts = iso(t);
    const has = {}, late = {};
    for (const e of L.occRange(first, last, { noTodos: true })) {
      const done = stOf(e.key) === 'done';
      for (let d = e.start; d <= e.end; d = addDays(d, 1)) { if (d < first || d > last) continue; has[iso(d)] = 1; }
      if (!done && e.end >= first && e.end <= last && iso(e.end) <= ts) late[iso(e.end)] = 1;
    }
    let h = '<div class="mini-head"><button data-act="miniPrev" title="이전 달">‹</button><span class="ttl">' + y + '년 ' + m + '월</span>' +
      '<span style="display:flex;gap:2px;align-items:center"><button class="today-btn" data-act="miniToday">오늘</button><button data-act="miniNext" title="다음 달">›</button></span></div>' +
      '<div class="wk">' + [...WD].map(c => '<span>' + c + '</span>').join('') + '</div><div class="cal7">';
    for (const wk of weeks) for (const d of wk) {
      const s = iso(d), hol = holName(d);
      h += '<div class="day' + (d.getMonth() + 1 !== m ? ' muted' : '') + (d.getDay() === 0 || hol ? ' sun' : d.getDay() === 6 ? ' sat' : '') +
        (s === ts ? ' today' : '') + (has[s] ? ' has' : '') + (late[s] ? ' late' : '') + '" data-act="miniDay" data-date="' + s + '"' +
        (hol ? ' title="' + esc(hol) + '"' : '') + '>' + d.getDate() + '</div>';
    }
    host.innerHTML = h + '</div>';
  }

  /* ── TO-DO 패널 (메인 / 미니 공용) ── */
  function todoCard() {
    return '<div class="side-title">3일 업무 TO-DO</div><div class="todo-scroll">' +
      '<div id="tdPastWrap"><div class="grp-t late">지난 미완료</div><div id="tdPast"></div></div>' +
      '<div class="grp-t" id="tdTodayT"></div><div class="quick"><input id="tdTodayIn" placeholder="할 일 입력 후 Enter"><button data-act="addTodo" data-k="today">＋</button></div><div id="tdToday"></div>' +
      '<div class="grp-t" id="tdTomT"></div><div class="quick"><input id="tdTomIn" placeholder="할 일 입력 후 Enter"><button data-act="addTodo" data-k="tomorrow">＋</button></div><div id="tdTom"></div></div>';
  }
  function todoRow(t, late) {
    return '<div class="tr ' + (t.done ? 'done' : '') + (late ? ' late' : '') + '"><button class="chk ' + (t.done ? 'on' : '') + '" data-act="tdToggle" data-id="' + t.id + '">' + (t.done ? '✓' : '') + '</button>' +
      '<span class="tx">' + esc(t.text) + '</span><button class="x mv" data-act="tdPush" data-id="' + t.id + '" title="다음 날로 미루기">›</button>' +
      '<button class="x" data-act="tdDel" data-id="' + t.id + '" title="삭제">✕</button></div>';
  }
  function renderTodos() {
    const t = today(), ts = iso(t), tm = iso(addDays(t, 1));
    const past = S.todos.filter(x => !x.done && x.date < ts);
    const fill = (id, items, late) => {
      const el = $('#' + id); if (!el) return;
      el.innerHTML = items.length ? items.sort((a, b) => (a.done - b.done) || (a.id - b.id)).map(x => todoRow(x, late)).join('') : (late ? '' : '<div class="tempty">없음</div>');
    };
    fill('tdPast', past, true);
    fill('tdToday', S.todos.filter(x => x.date === ts), false);
    fill('tdTom', S.todos.filter(x => x.date === tm), false);
    $('#tdPastWrap').classList.toggle('hidden', !past.length);
    $('#tdTodayT').textContent = '오늘 (' + pad2(t.getMonth() + 1) + '/' + pad2(t.getDate()) + ')';
    const n = addDays(t, 1);
    $('#tdTomT').textContent = '내일 (' + pad2(n.getMonth() + 1) + '/' + pad2(n.getDate()) + ')';
  }
  const pad2 = n => String(n).padStart(2, '0');

  /* ── 탭 ── */
  function renderTabs() {
    const host = $('#tabs'); if (!host) return;
    const n = L.doingList().length;
    host.innerHTML = [['prog', '진행'], ['all', '전체 조회'], ['cal', '업무 달력'], ['log', '근무일지'], ['stat', '통계']].map(([k, name]) =>
      '<button class="tab ' + (ui.tab === k ? 'active' : '') + '" data-act="tab" data-tab="' + k + '">' + name +
      (k === 'prog' ? '<span class="cnt">' + n + '</span>' : '') + '</button>').join('');
  }
  function renderPanel() {
    const p = $('#panel'); if (!p) return;
    const sc = p.scrollTop;
    p.innerHTML = ({ prog: viewProg, all: viewAll, cal: viewCal, log: viewLog, stat: viewStats })[ui.tab]();
    p.scrollTop = sc;
  }

  /* 진행 */
  function viewProg() {
    const list = L.doingList();
    let h = '<div class="sec-head"><div><h2>진행</h2><div class="sub">지금 하고 있는 업무예요 · 시작은 \'전체 조회\'에서 해요</div></div></div>';
    if (!list.length) return h + '<div class="empty"><div><b>진행 중인 업무가 없어요</b>전체 조회에서 \'진행\' 버튼을 누르면 여기에 나타나요</div></div>';
    h += '<div class="table"><div class="rw head prog"><div>업무</div><div>기간</div><div>마감</div><div></div></div>';
    for (const o of list) {
      h += '<div class="rw prog ' + (L.pinkOf(o) ? 'pink' : '') + '"><div class="c-t">' + esc(o.title) + '</div><div class="c-p">' + periodText(o) +
        '</div><div class="c-m">' + dueCell(o) + '</div><div class="c-a"><button class="action finish" data-act="finish" data-key="' + o.key + '">✓ 완료</button>' +
        '<button class="undo" data-act="reset" data-key="' + o.key + '" title="시작을 취소하고 시작 전으로 되돌려요">취소</button></div></div>';
    }
    return h + '</div>';
  }

  /* 전체 조회 */
  function viewAll() {
    const y = ui.listY, m = ui.listM;
    const list = L.occRange(D(y, m, 1), D(y, m, mlen(y, m)), { noTodos: true }).sort((a, b) => {
      const ad = stOf(a.key) === 'done', bd = stOf(b.key) === 'done';
      return ad !== bd ? (ad ? 1 : -1) : L.byEnd(a, b);
    });
    let h = '<div class="sec-head"><div><h2>전체 조회</h2><div class="sub">' + y + '년 ' + m + '월 업무 달력에 등록된 업무 ' + list.length + '건 · 마감 당일 미완료는 진분홍색으로 표시돼요</div></div>' +
      '<div class="nav"><button data-act="listPrev">‹</button><span class="lbl">' + y + '.' + pad2(m) + '</span><button data-act="listNext">›</button><button data-act="listToday">이번 달</button></div></div>';
    if (!list.length) return h + '<div class="empty"><div><b>이 달에 등록된 업무가 없어요</b>\'업무 달력\' 탭에서 업무를 등록해 보세요</div></div>';
    h += '<div class="table"><div class="rw head all"><div>업무</div><div>기간</div><div>마감</div><div style="text-align:right">상태</div></div>';
    for (const o of list) {
      const st = stOf(o.key);
      h += '<div class="rw all ' + (L.pinkOf(o) ? 'pink' : '') + (st === 'done' ? ' done' : '') + '"><div class="c-t">' + esc(o.title) + '</div><div class="c-p">' + periodText(o) +
        '</div><div class="c-m">' + dueCell(o) + '</div><div class="c-a">' + stateCell(o) + '</div></div>';
    }
    return h + '</div>';
  }

  /* 업무 달력 */
  function viewCal() {
    const y = ui.calY, m = ui.calM, weeks = monthWeeks(y, m), ts = iso(today());
    const evs = L.occRange(weeks[0][0], weeks[weeks.length - 1][6]);
    let h = '<div class="sec-head"><div><h2>업무 달력</h2><div class="legend"><span><i style="background:#e8edf8"></i>시작 전</span><span><i style="background:#b9c8f1"></i>진행</span>' +
      '<span><i style="background:var(--mint)"></i>완료</span><span><i style="background:var(--pink)"></i>마감 당일·지연</span><span><i style="background:var(--butter)"></i>할 일</span></div></div>' +
      '<div class="nav"><button data-act="calPrev">‹</button><span class="lbl">' + y + '년 ' + m + '월</span><button data-act="calNext">›</button><button data-act="calToday">오늘</button>' +
      '<span style="width:8px"></span><button data-act="holidays">휴일 추가</button><button data-act="manage">업무 관리</button><button class="btn primary" data-act="addTask">＋ 업무 등록</button></div></div>' +
      '<div class="cal-wrap"><div class="cal-wk">' + [...WD].map(c => '<div>' + c + '</div>').join('') + '</div><div class="cal-grid">';
    for (const wk of weeks) {
      const ws = wk[0], we = wk[6];
      const segs = evs.filter(e => !(e.end < ws || e.start > we)).sort((a, b) => (a.start - b.start) || ((b.end - b.start) - (a.end - a.start)) || a.kind.localeCompare(b.kind));
      const lanes = []; let bars = '';
      for (const e of segs) {
        const cs = Math.max(diffDays(e.start, ws), 0), ce = Math.min(diffDays(e.end, ws), 6);
        let lane = lanes.findIndex(last => last < cs);
        if (lane < 0) { lanes.push(ce); lane = lanes.length - 1; } else lanes[lane] = ce;
        let cls;
        if (e.kind === 'todo') cls = 'todo';
        else { const st = stOf(e.key); cls = st === 'done' ? 'done' : L.pinkOf(e) ? 'pink' : st === 'doing' ? 'doing' : 'ready'; }
        bars += '<div class="bar ' + cls + (e.start < ws ? ' cl' : '') + (e.end > we ? ' cr' : '') + '" style="grid-column:' + (cs + 1) + '/' + (ce + 2) + ';grid-row:' + (lane + 1) +
          '" title="' + esc(e.title) + '">' + (cls === 'done' ? '✓ ' : '') + esc(e.title) + '</div>';
      }
      h += '<div class="week" style="--n:' + lanes.length + '"><div class="cells">';
      for (const d of wk) {
        const hn = holName(d), off = d.getDay() === 0 || d.getDay() === 6 || hn;
        h += '<div class="cell' + (d.getMonth() + 1 !== m ? ' other' : '') + (off ? ' off' : '') + (iso(d) === ts ? ' today' : '') + '" data-act="day" data-date="' + iso(d) + '">' +
          '<span class="dn' + (d.getDay() === 0 || hn ? ' red' : d.getDay() === 6 ? ' blue' : '') + '">' + d.getDate() + '</span>' + (hn ? '<span class="hn">' + esc(hn) + '</span>' : '') + '</div>';
      }
      h += '</div><div class="bars">' + bars + '</div></div>';
    }
    return h + '</div></div>';
  }

  /* 근무일지: 그날 완료 처리한 업무 + 체크한 할 일을 자동으로 모아요 */
  function logText(ds) {
    const items = [];
    for (const k of Object.keys(S.prog)) {
      const p = S.prog[k];
      if (p.s === 'done' && p.done_at === ds) { const o = L.occByKey(k); if (o) items.push(o); }
    }
    items.sort(L.byEnd);
    const todos = S.todos.filter(x => x.done && x.date === ds).sort((a, b) => a.id - b.id);
    const lines = items.map(o => o.title).concat(todos.map(x => x.text));
    return { text: lines.join('\n'), count: lines.length };
  }
  function focusLog() { setTimeout(() => { const ta = $('#logText'); if (ta) { ta.focus(); ta.select(); } }, 0); }
  function viewLog() {
    const ds = ui.logDate || iso(today()), d = P(ds), isToday = ds === iso(today());
    const r = logText(ds);
    return '<div class="sec-head"><div><h2>근무일지</h2><div class="sub">' + (isToday ? '오늘' : (d.getMonth() + 1) + '월 ' + d.getDate() + '일') +
      ' 완료한 업무 ' + r.count + '건이 자동으로 모여요 · 아래 칸을 클릭하고 Ctrl+A → Ctrl+C</div></div>' +
      '<div class="nav"><button data-act="logPrev">‹</button><span class="lbl">' + (d.getMonth() + 1) + '/' + d.getDate() + '(' + WD[d.getDay()] + ')</span>' +
      '<button data-act="logNext">›</button><button data-act="logToday">오늘</button><button class="btn primary" data-act="logCopy">복사</button></div></div>' +
      '<textarea id="logText" class="logbox" readonly spellcheck="false">' + esc(r.text) + '</textarea>' +
      (r.count ? '' : '<div class="sub" style="margin-top:8px">아직 완료한 업무가 없어요. 진행 탭에서 ✓완료를 누르면 여기에 담겨요.</div>');
  }

  /* 통계 */
  function viewStats() {
    const y = ui.statY, m = ui.statM, t = today();
    const list = L.occRange(D(y, m, 1), D(y, m, mlen(y, m)), { noTodos: true });
    let late = 0, run = 0, done = 0, plan = 0;
    for (const o of list) {
      const st = stOf(o.key);
      if (st === 'done') done++;
      else { if (o.end < t) late++; if (st === 'doing') run++; else plan++; }
    }
    const total = list.length, max = Math.max(total, 1), rate = total ? Math.round(done / total * 100) : 0;
    const card = (label, num, color) => '<div class="stat"><div class="label"><i style="background:' + color + '"></i>' + label + '</div><div class="num" style="color:' + color + '">' + num + '</div></div>';
    const bar = (label, n, color) => '<div class="brow"><div class="bl">' + label + '</div><div class="bt"><div class="bf" style="width:' + Math.round(n / max * 100) + '%;background:' + color + '"></div></div><b>' + n + '</b></div>';
    return '<div class="sec-head"><div><h2>통계</h2><div class="sub">' + y + '년 ' + m + '월 업무 달력 기준</div></div>' +
      '<div class="nav"><button data-act="statPrev">‹</button><span class="lbl">' + y + '.' + pad2(m) + '</span><button data-act="statNext">›</button><button data-act="statToday">이번 달</button></div></div>' +
      '<div class="stats">' + card('전체 업무', total, '#6f7fb8') + card('지연', late, '#d9548f') + card('진행', run, '#6c88d6') + card('완료', done, '#5fa384') + card('시작 전', plan, '#c9a23d') + '</div>' +
      '<div class="chartbox"><div class="ct"><strong>업무 상태 비율</strong><span class="rate">완료율 ' + rate + '%</span></div>' +
      bar('지연', late, '#f09bc0') + bar('진행', run, '#9db2ec') + bar('완료', done, '#a9d4bd') + bar('시작 전', plan, '#ecd48f') + '</div>';
  }

  /* ── 미니창 ── */
  function renderMini() {
    const t = today(), ts = iso(t);
    const doing = L.doingList(), late = L.lateList();
    const dueToday = L.occRange(t, t, { noTodos: true }).filter(o => iso(o.end) === ts && stOf(o.key) !== 'done');
    const map = new Map();
    [...late, ...doing, ...dueToday].forEach(o => map.set(o.key, o));
    const list = [...map.values()].sort((a, b) => (L.pinkOf(a) ? 0 : 1) - (L.pinkOf(b) ? 0 : 1) || L.byEnd(a, b));
    $('#miniSummary').innerHTML = '<div class="pills"><div class="pill p-pink"><b>' + dueToday.length + '</b><span>오늘 마감</span></div>' +
      '<div class="pill p-blue"><b>' + doing.length + '</b><span>진행</span></div><div class="pill"><b>' + late.length + '</b><span>지연</span></div></div>';
    let h = '';
    if (!list.length) h = '<div class="tempty">지금 처리할 업무가 없어요</div>';
    for (const o of list) {
      const n = diffDays(o.end, t), st = stOf(o.key), pk = L.pinkOf(o);
      const sub = pk === 'today' ? '오늘 마감' : pk === 'late' ? '지연 D+' + (-n) : 'D-' + n + ' · ' + fmtMD(o.end) + ' 마감';
      h += '<div class="mt-row ' + (pk ? 'pink' : '') + '"><div class="t">' + esc(o.title) + '<small>' + sub + '</small></div>' +
        (st === 'doing' ? '<button class="action finish" data-act="finish" data-key="' + o.key + '">완료</button>'
          : '<button class="action start" data-act="start" data-key="' + o.key + '">진행</button>') + '</div>';
    }
    $('#miniTasks').innerHTML = h;
  }

  /* ── 전체 렌더 ── */
  function render() {
    renderTodos();
    if (MODE === 'main') { renderMiniCal(); renderTabs(); renderPanel(); } else renderMini();
    if (curModal && curModal.refresh) curModal.refresh();
  }

  function buildShell() {
    const root = $('#root');
    if (MODE === 'main') {
      root.innerHTML = '<div class="app"><div class="topbar"><div class="brand">▣ WORK SPACE</div><div class="top-actions"><span class="today-text" id="todayText"></span>' +
        '<button class="btn" data-act="toggleMini">미니창</button></div></div>' +
        '<div class="note-card"><div class="note-title">업무 참고 메모</div><textarea id="memo" spellcheck="false" placeholder="자주 보는 내용이나 기억할 것을 적어두세요"></textarea></div>' +
        '<div class="layout"><aside class="sidebar"><div class="side-cal" id="miniCal"></div><div class="side-todo">' + todoCard() + '</div></aside>' +
        '<main class="main"><div class="tabs" id="tabs"></div><div class="panel" id="panel"></div></main></div></div>';
      const n = today();
      $('#todayText').textContent = n.getFullYear() + '년 ' + (n.getMonth() + 1) + '월 ' + n.getDate() + '일 ' + WD[n.getDay()] + '요일';
    } else {
      root.innerHTML = '<div class="mini-app"><div class="mini-top"><div class="brand sm">▣ WORK SPACE<span>MINI</span></div>' +
        '<button class="pinbtn on" data-act="pin">항상 위</button></div>' +
        '<section class="mini-card"><div class="mt">오늘 현황</div><div id="miniSummary"></div></section>' +
        '<section class="mini-card mini-tasks"><div class="mt">업무</div><div class="body" id="miniTasks"></div></section>' +
        '<section class="mini-card mini-todo"><div class="side-todo">' + todoCard() + '</div></section></div>';
    }
    ['tdTodayIn', 'tdTomIn'].forEach(id => {
      const i = document.getElementById(id);
      if (i) i.addEventListener('keydown', e => { if (e.key === 'Enter') acts.addTodo({ dataset: { k: id === 'tdTodayIn' ? 'today' : 'tomorrow' } }); });
    });
    const memo = $('#memo');
    if (memo) {
      let tm;
      const save = () => { S.memo = memo.value; persist(); };
      memo.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(save, 400); });
      memo.addEventListener('blur', save);
    }
  }

  /* 다른 창에서 데이터가 바뀌었을 때 */
  window.__onState = function (s) {
    S = L.migrate(s); L.setState(S);
    const memo = $('#memo');
    if (memo && document.activeElement !== memo) memo.value = S.memo;
    render();
  };

  async function boot() {
    const r = await loadAll();
    L.setHol(r.holidays || {});
    S = L.migrate(r.state); L.setState(S);
    buildShell();
    const memo = $('#memo'); if (memo) memo.value = S.memo;
    render();
    lastDay = iso(today());
    setInterval(() => { if (iso(today()) !== lastDay) { lastDay = iso(today()); render(); } }, 60000);
    window.__WS_READY = true;
  }

  let booted = false;
  const go = () => { if (!booted) { booted = true; boot(); } };
  window.addEventListener('pywebviewready', go);
  let tries = 0;
  const iv = setInterval(() => {
    tries++;
    if (hasPy()) { clearInterval(iv); go(); }
    else if (tries > 15 && !window.pywebview) { clearInterval(iv); go(); }
  }, 100);
})();
'''

PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WORK SPACE</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>@@STYLE@@</style></head>
<body><div id="root"></div>
<script>window.WS_MODE='@@MODE@@';</script>
<script>@@LOGICJS@@</script>
<script>@@APPJS@@</script>
</body></html>"""


def page(mode):
    return (PAGE.replace("@@STYLE@@", CSS).replace("@@MODE@@", mode)
            .replace("@@LOGICJS@@", LOGIC_JS).replace("@@APPJS@@", APP_JS))


class Core:
    def __init__(self):
        self.lock = threading.Lock()
        self.windows = {}
        self.quitting = False
        self.mini_visible = True

    def read(self):
        try:
            with open(DATA_PATH, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception:
            try:
                os.replace(DATA_PATH, DATA_PATH + ".broken")
            except OSError:
                pass
            return {}

    def write(self, state):
        with self.lock:
            tmp = DATA_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=1)
            os.replace(tmp, DATA_PATH)

    def broadcast(self, state, source):
        payload = json.dumps(state)  # ensure_ascii=True → JS에 안전하게 삽입
        for name, w in list(self.windows.items()):
            if name == source:
                continue
            try:
                w.evaluate_js("window.__onState && window.__onState(%s)" % payload)
            except Exception:
                pass

    def show_mini(self, show):
        w = self.windows.get("mini")
        if not w:
            return
        try:
            w.show() if show else w.hide()
            self.mini_visible = show
        except Exception:
            pass


class Api:
    """화면(JS)에서 호출하는 함수들. 밑줄(_)로 시작하는 속성은 JS에 노출되지 않습니다."""

    def __init__(self, core):
        self._core = core

    def load_state(self):
        return {"state": self._core.read(), "holidays": HOLIDAYS}

    def save_state(self, state, source):
        self._core.write(state)
        self._core.broadcast(state, source)
        return True

    def toggle_mini(self):
        self._core.show_mini(not self._core.mini_visible)
        return True

    def set_topmost(self, on):
        w = self._core.windows.get("mini")
        if w:
            try:
                w.on_top = bool(on)
            except Exception:
                pass
        return True


def main():
    if os.path.exists(DATA_PATH):  # 실행할 때마다 직전 데이터를 백업
        try:
            shutil.copyfile(DATA_PATH, DATA_PATH + ".bak")
        except OSError:
            pass
    core = Core()
    main_w = webview.create_window(APP_TITLE, html=page("main"), js_api=Api(core), width=1320, height=860,
                                   min_size=(1100, 720), background_color="#f2f1f6")
    mini_w = webview.create_window(APP_TITLE + " MINI", html=page("mini"), js_api=Api(core), width=360, height=740,
                                   min_size=(320, 520), on_top=True, background_color="#f2f1f6")
    core.windows = {"main": main_w, "mini": mini_w}

    def on_main_closing():
        core.quitting = True
        try:
            mini_w.destroy()
        except Exception:
            pass

    def on_mini_closing():
        if core.quitting:
            return True
        core.show_mini(False)
        return False  # 닫기(X)는 숨기기로 처리 → 메인창의 '미니창' 버튼으로 다시 열기

    main_w.events.closing += on_main_closing
    mini_w.events.closing += on_mini_closing
    webview.start()


if __name__ == "__main__":
    main()
