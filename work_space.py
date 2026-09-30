# -*- coding: utf-8 -*-
"""
WORK SPACE - 개인 업무 관리 프로그램 (Python + tkinter, 서버 불필요)

- 메인창 : 업무 참고 메모 / 미니 달력 / 3일 TO-DO / 메모장 / 진행건 관리 / 전체 조회 / 업무 달력 / 통계
- 미니창 : 오늘 현황 / 3일 TO-DO / 메모장 (항상 위 고정 가능)
- 업무 달력 : 주말·공휴일이 마감일이면 직전 평일로 자동 이동, 기간형 일정은 기간 막대로 표시
- 데이터 : exe(또는 .py)와 같은 폴더의 workspace_data.json 에 자동 저장
"""
import calendar
import datetime as dt
import json
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from collections import namedtuple
from tkinter import messagebox, ttk

# ─────────────────────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────────────────────
WD = "월화수목금토일"          # date.weekday() 인덱스용
WD_SUN = "일월화수목금토"      # 달력 헤더(일요일 시작)

C = dict(
    bg="#f3f4f6", panel="#ffffff", line="#d8dce2", text="#1f2937", sub="#6b7280",
    accent="#2f5fd0", accent_bg="#e6edfb", red="#d0403f", blue="#2f5fd0",
    green="#2a8a63", gray="#9ca3af", warn="#d9822b",
)
KIND_STYLE = {   # kind: (배경, 기간 배경, 글자색)
    "case": ("#dbe6fb", "#b7cbf3", "#1c3b8a"),
    "done": ("#e5e7eb", "#d1d5db", "#6b7280"),
    "rule": ("#d8f0e4", "#b5e2cb", "#17593d"),
    "todo": ("#fdecd2", "#fdecd2", "#7a4a00"),
}
KIND_TAG = {"case": "[진행건]", "done": "[완료]", "rule": "[반복]", "todo": "[할일]"}


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_PATH = os.path.join(app_dir(), "workspace_data.json")

# ─────────────────────────────────────────────────────────────
# 날짜 / 공휴일 유틸
# ─────────────────────────────────────────────────────────────
try:
    import holidays as _holidays
    _KR = _holidays.country_holidays("KR")
    HAS_HOLIDAYS = True
except Exception:  # 라이브러리가 없으면 양력 고정 공휴일만 사용
    _KR = None
    HAS_HOLIDAYS = False

_FIXED = {(1, 1): "신정", (3, 1): "삼일절", (5, 5): "어린이날", (6, 6): "현충일",
          (8, 15): "광복절", (10, 3): "개천절", (10, 9): "한글날", (12, 25): "성탄절"}
EXTRA_OFF = {}   # 사용자가 추가한 휴일 {date: 이름}


def iso(d):
    return d.isoformat() if d else ""


def from_iso(s):
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        return None


def parse_date(s):
    """'2026-10-05', '10-05', '1005', '10/5' 등을 date로. 빈 값은 None, 형식 오류는 ValueError."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    year = dt.date.today().year
    m = re.fullmatch(r"(\d{1,2})[-./ ](\d{1,2})", s)
    if m:
        mo, da = int(m.group(1)), int(m.group(2))
    elif re.fullmatch(r"\d{4}", s):
        mo, da = int(s[:2]), int(s[2:])
    else:
        raise ValueError(s)
    return dt.date(year, mo, da)


def fmt_d(d):
    if d is None:
        return ""
    base = f"{d:%m-%d}" if d.year == dt.date.today().year else f"{d:%Y-%m-%d}"
    return f"{base}({WD[d.weekday()]})"


def holiday_name(d):
    if d in EXTRA_OFF:
        return EXTRA_OFF[d]
    if _KR is not None:
        n = _KR.get(d)
        if n:
            return n.split(",")[0].strip()
        return ""
    return _FIXED.get((d.month, d.day), "")


def is_off(d):
    return d.weekday() >= 5 or bool(holiday_name(d))


def prev_workday(d):
    """d가 주말/공휴일이면 직전 평일로."""
    for _ in range(40):
        if not is_off(d):
            return d
        d -= dt.timedelta(days=1)
    return d


def month_len(y, m):
    return calendar.monthrange(y, m)[1]


def shift_month(y, m, k):
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


# ─────────────────────────────────────────────────────────────
# 일정 계산 (진행건 / 반복 업무 / 할 일)
# ─────────────────────────────────────────────────────────────
Ev = namedtuple("Ev", "title start end kind ref")


def case_span(c):
    """진행건의 (시작, 마감) — 마감이 휴일이면 직전 평일로 조정. 날짜 없으면 (None, None)."""
    start, due = from_iso(c.get("start")), from_iso(c.get("due"))
    if due and c.get("adjust", True):
        due = prev_workday(due)
    s, e = start or due, due or start
    if s is None:
        return None, None
    if s > e:
        s = e
    return s, e


def case_end(c):
    return case_span(c)[1]


def rule_occurrence(r, y, m):
    """반복 업무 규칙의 y년 m월 발생 (시작, 종료) — 없으면 None."""
    ml = month_len(y, m)
    t = r.get("type")
    a, b = int(r.get("a", 1)), int(r.get("b", 1))
    if t == "monthly":                       # 매월 N일 → 휴일이면 직전 평일
        d = prev_workday(dt.date(y, m, min(max(a, 1), ml)))
        return d, d
    if t == "eom":                           # 월말 마지막 영업일 기준 N영업일 전
        d = prev_workday(dt.date(y, m, ml))
        for _ in range(max(a, 0)):
            d = prev_workday(d - dt.timedelta(days=1))
        return d, d
    if t == "period":                        # 매월 a일 ~ b일 (종료일이 휴일이면 직전 평일)
        s = dt.date(y, m, min(max(a, 1), ml))
        ey, em = (y, m) if b >= a else shift_month(y, m, 1)
        e0 = dt.date(ey, em, min(max(b, 1), month_len(ey, em)))
        e = prev_workday(e0)
        if e < s:
            s = e
        return s, e
    return None


def describe_rule(r):
    a, b, t = r.get("a", 1), r.get("b", 1), r.get("type")
    if t == "monthly":
        return f"매월 {a}일 (휴일이면 직전 평일)"
    if t == "eom":
        return "월말 마지막 영업일" if int(a) == 0 else f"월말 마지막 영업일 기준 {a}영업일 전"
    return f"매월 {a}일 ~ {b}일 (종료일이 휴일이면 직전 평일)"


def events_between(store, d1, d2):
    out = []
    for c in store.d["cases"]:
        s, e = case_span(c)
        if s is None or e < d1 or s > d2:
            continue
        name = c.get("company", "") + (" · " + c["title"] if c.get("title") else "")
        out.append(Ev(name, s, e, "done" if c.get("done") else "case", c["id"]))
    months, (y, m) = [], shift_month(d1.year, d1.month, -1)
    while (y, m) <= (d2.year, d2.month):
        months.append((y, m))
        y, m = shift_month(y, m, 1)
    for r in store.d["rules"]:
        for (y, m) in months:
            occ = rule_occurrence(r, y, m)
            if occ and not (occ[1] < d1 or occ[0] > d2):
                title = (r.get("time", "") + " " if r.get("time") else "") + r.get("title", "")
                out.append(Ev(title, occ[0], occ[1], "rule", r["id"]))
    for t in store.d["todos"]:
        d = from_iso(t.get("date"))
        if d and not t.get("done") and d1 <= d <= d2:
            out.append(Ev(t["text"], d, d, "todo", t["id"]))
    return out


def overdue_count(store):
    today = dt.date.today()
    n = 0
    for c in store.d["cases"]:
        e = case_end(c)
        if not c.get("done") and e and e < today:
            n += 1
    return n


# ─────────────────────────────────────────────────────────────
# 데이터 저장소
# ─────────────────────────────────────────────────────────────
class Store:
    DEFAULT = {"memo": "", "notepad": "", "todos": [], "cases": [], "rules": [],
               "extra_off": [], "cats": ["일반", "긴급", "정기"], "next_id": 1, "geo": {}}

    def __init__(self, path):
        self.path = path
        self.d = json.loads(json.dumps(self.DEFAULT))
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.d.update(json.load(f))
            except Exception:
                try:
                    os.replace(path, path + ".broken")
                except OSError:
                    pass
        self.sync_extra()

    def sync_extra(self):
        EXTRA_OFF.clear()
        for it in self.d["extra_off"]:
            d = from_iso(it.get("date"))
            if d:
                EXTRA_OFF[d] = it.get("name") or "휴일"

    def nid(self):
        n = self.d["next_id"]
        self.d["next_id"] = n + 1
        return n

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError as ex:
            messagebox.showerror("저장 실패", str(ex))


# ─────────────────────────────────────────────────────────────
# 공용 위젯
# ─────────────────────────────────────────────────────────────
def make_btn(parent, text, cmd, accent=False, small=False):
    return tk.Button(
        parent, text=text, command=cmd, relief="flat", cursor="hand2",
        bg=C["accent"] if accent else "#e5e7eb", fg="#fff" if accent else C["text"],
        activebackground="#244fb3" if accent else "#d1d5db",
        activeforeground="#fff" if accent else C["text"],
        padx=6 if small else 12, pady=2 if small else 4, bd=0)


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=bg)
        self.win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))


class MemoBox(tk.Frame):
    """store.d[key] 와 자동 동기화되는 메모 입력창 (메인/미니 공유)."""

    def __init__(self, parent, app, key, title, height):
        super().__init__(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        self.app, self.key, self.job = app, key, None
        tk.Label(self, text=title, bg=C["panel"], fg=C["text"], font=app.font_b).pack(anchor="w", padx=8, pady=(6, 0))
        self.text = tk.Text(self, height=height, wrap="word", relief="flat", undo=True, padx=6, pady=4,
                            bg="#fff", highlightthickness=0, font=app.font)
        self.text.pack(fill="both", expand=True, padx=6, pady=6)
        self.text.insert("1.0", app.store.d[key])
        self.text.bind("<KeyRelease>", self._changed)
        self.text.bind("<FocusOut>", self._flush)
        app.memos.append(self)

    def _changed(self, _e=None):
        if self.job:
            self.after_cancel(self.job)
        self.job = self.after(500, self._flush)

    def _flush(self, _e=None):
        if self.job:
            self.after_cancel(self.job)
            self.job = None
        val = self.text.get("1.0", "end-1c")
        if val != self.app.store.d[self.key]:
            self.app.store.d[self.key] = val
            self.app.store.save()
            self.app.sync_memos(self)

    def sync(self):
        val = self.app.store.d[self.key]
        if self.text.get("1.0", "end-1c") != val:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", val)


class TodoPanel(tk.Frame):
    """지난 미완료 / 오늘 / 내일 TO-DO."""

    def __init__(self, parent, app, wrap=190):
        super().__init__(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        self.app, self.wrap = app, wrap
        tk.Label(self, text="3일 업무 TO-DO", bg=C["panel"], fg=C["text"], font=app.font_b).pack(anchor="w", padx=8, pady=(6, 2))
        self.sf = ScrollFrame(self, C["panel"])
        self.sf.pack(fill="both", expand=True)
        inner = self.sf.inner
        self.hdr, self.lst, self.ent = {}, {}, {}
        for key in ("past", "today", "tomorrow"):
            self.hdr[key] = tk.Label(inner, bg=C["panel"], fg=C["accent"], font=app.font_b, anchor="w")
            self.hdr[key].pack(fill="x", padx=8, pady=(6, 2))
            if key != "past":
                e = tk.Entry(inner, relief="solid", bd=1, highlightthickness=0, font=app.font)
                e.pack(fill="x", padx=8, pady=(0, 3), ipady=2)
                e.bind("<Return>", lambda ev, k=key: self.add(k))
                self.ent[key] = e
            self.lst[key] = tk.Frame(inner, bg=C["panel"])
            self.lst[key].pack(fill="x")
        app.refreshables.append(self)

    def add(self, key):
        text = self.ent[key].get().strip()
        if not text:
            return
        d = dt.date.today() + dt.timedelta(days=1 if key == "tomorrow" else 0)
        st = self.app.store
        st.d["todos"].append({"id": st.nid(), "text": text, "date": iso(d), "done": False})
        self.ent[key].delete(0, "end")
        st.save()
        self.app.refresh_all()

    def toggle(self, t, val):
        t["done"] = bool(val)
        self.app.store.save()
        self.app.refresh_all()

    def delete(self, t):
        self.app.store.d["todos"].remove(t)
        self.app.store.save()
        self.app.refresh_all()

    def push(self, t):
        d = from_iso(t["date"]) or dt.date.today()
        today = dt.date.today()
        t["date"] = iso(today if d < today else d + dt.timedelta(days=1))
        self.app.store.save()
        self.app.refresh_all()

    def refresh(self):
        today = dt.date.today()
        tom = today + dt.timedelta(days=1)
        self.hdr["past"].config(text="지난 미완료")
        self.hdr["today"].config(text=f"오늘 ({today:%m/%d})")
        self.hdr["tomorrow"].config(text=f"내일 ({tom:%m/%d})")
        todos = self.app.store.d["todos"]
        groups = {
            "past": [t for t in todos if (from_iso(t["date"]) or today) < today and not t["done"]],
            "today": [t for t in todos if from_iso(t["date"]) == today],
            "tomorrow": [t for t in todos if from_iso(t["date"]) == tom],
        }
        for key, items in groups.items():
            for w in self.lst[key].winfo_children():
                w.destroy()
            for t in sorted(items, key=lambda x: (x["done"], x["id"])):
                self._row(self.lst[key], t)
        # 지난 미완료가 없으면 제목 숨김
        if groups["past"]:
            self.hdr["past"].pack(fill="x", padx=8, pady=(6, 2), before=self.hdr["today"])
            self.lst["past"].pack(fill="x", before=self.hdr["today"])
        else:
            self.hdr["past"].pack_forget()
            self.lst["past"].pack_forget()

    def _row(self, parent, t):
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=6, pady=1)
        var = tk.BooleanVar(value=t["done"])
        tk.Checkbutton(row, variable=var, bg=C["panel"], activebackground=C["panel"],
                       command=lambda: self.toggle(t, var.get())).pack(side="left")
        f = self.app.font_done if t["done"] else self.app.font
        tk.Label(row, text=t["text"], anchor="w", justify="left", wraplength=self.wrap, bg=C["panel"],
                 fg=C["gray"] if t["done"] else C["text"], font=f).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="✕", relief="flat", bg=C["panel"], fg=C["red"], bd=0, cursor="hand2",
                  command=lambda: self.delete(t)).pack(side="right")
        tk.Button(row, text="▶", relief="flat", bg=C["panel"], fg=C["sub"], bd=0, cursor="hand2",
                  command=lambda: self.push(t)).pack(side="right")


class MiniCal(tk.Frame):
    """왼쪽 작은 달력. 일정 있는 날은 굵게+점, 클릭하면 업무 달력으로 이동."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        self.app = app
        today = dt.date.today()
        self.y, self.m = today.year, today.month
        head = tk.Frame(self, bg=C["panel"])
        head.pack(fill="x", padx=6, pady=(6, 2))
        tk.Button(head, text="◀", relief="flat", bg=C["panel"], bd=0, command=lambda: self.move(-1)).pack(side="left")
        tk.Button(head, text="▶", relief="flat", bg=C["panel"], bd=0, command=lambda: self.move(1)).pack(side="right")
        self.title = tk.Label(head, bg=C["panel"], font=app.font_b)
        self.title.pack(side="left", expand=True)
        grid = tk.Frame(self, bg=C["panel"])
        grid.pack(padx=6, pady=(0, 6))
        for j, n in enumerate(WD_SUN):
            tk.Label(grid, text=n, width=4, bg=C["panel"], fg=C["red"] if j == 0 else C["blue"] if j == 6 else C["sub"],
                     font=app.font_s).grid(row=0, column=j)
        self.cells = [[None] * 7 for _ in range(6)]
        self.dates = [[None] * 7 for _ in range(6)]
        for i in range(6):
            for j in range(7):
                lb = tk.Label(grid, text="", width=4, bg=C["panel"], font=app.font_s, cursor="hand2")
                lb.grid(row=i + 1, column=j, pady=1)
                lb.bind("<Button-1>", lambda e, i=i, j=j: self.click(i, j))
                self.cells[i][j] = lb
        app.refreshables.append(self)

    def move(self, k):
        self.y, self.m = shift_month(self.y, self.m, k)
        self.refresh()

    def click(self, i, j):
        d = self.dates[i][j]
        if d:
            self.app.goto(d)

    def refresh(self):
        self.title.config(text=f"{self.y}년 {self.m}월")
        weeks = calendar.Calendar(6).monthdatescalendar(self.y, self.m)
        has = set()
        for e in events_between(self.app.store, weeks[0][0], weeks[-1][-1]):
            d = max(e.start, weeks[0][0])
            while d <= min(e.end, weeks[-1][-1]):
                has.add(d)
                d += dt.timedelta(days=1)
        today = dt.date.today()
        for i in range(6):
            for j in range(7):
                lb = self.cells[i][j]
                if i >= len(weeks):
                    self.dates[i][j] = None
                    lb.config(text="", bg=C["panel"])
                    continue
                d = weeks[i][j]
                self.dates[i][j] = d
                fg = C["red"] if (j == 0 or holiday_name(d)) else C["blue"] if j == 6 else C["text"]
                if d.month != self.m:
                    fg = C["gray"]
                bg, font = C["panel"], self.app.font_s
                if d in has:
                    font = self.app.font_sb
                if d == today:
                    bg, fg = C["accent"], "#fff"
                lb.config(text=f"{d.day}" + ("·" if d in has else ""), fg=fg, bg=bg, font=font)


# ─────────────────────────────────────────────────────────────
# 업무 달력 (탭)
# ─────────────────────────────────────────────────────────────
class CalendarView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        today = dt.date.today()
        self.y, self.m = today.year, today.month
        self.hit = []
        bar = tk.Frame(self, bg=C["bg"])
        bar.pack(fill="x", pady=(8, 6), padx=6)
        make_btn(bar, "◀", lambda: self.move(-1), small=True).pack(side="left")
        self.title = tk.Label(bar, bg=C["bg"], font=app.font_title, width=12)
        self.title.pack(side="left", padx=6)
        make_btn(bar, "▶", lambda: self.move(1), small=True).pack(side="left")
        make_btn(bar, "오늘", self.today, small=True).pack(side="left", padx=(8, 0))
        make_btn(bar, "휴일 추가", lambda: HolidayDialog(app), small=True).pack(side="right")
        make_btn(bar, "반복 업무 관리", lambda: RuleManager(app), accent=True, small=True).pack(side="right", padx=6)
        legend = tk.Frame(self, bg=C["bg"])
        legend.pack(fill="x", padx=8)
        for kind, name in (("case", "진행건(기간)"), ("rule", "반복 업무"), ("todo", "할 일"), ("done", "완료")):
            tk.Label(legend, text="■", fg=KIND_STYLE[kind][1], bg=C["bg"]).pack(side="left")
            tk.Label(legend, text=name + "  ", fg=C["sub"], bg=C["bg"], font=app.font_s).pack(side="left")
        tk.Label(legend, text="※ 마감일이 주말·공휴일이면 직전 평일로 자동 이동", fg=C["sub"], bg=C["bg"],
                 font=app.font_s).pack(side="right")
        self.cv = tk.Canvas(self, bg="#fff", highlightthickness=1, highlightbackground=C["line"])
        self.cv.pack(fill="both", expand=True, padx=6, pady=6)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<Button-1>", self.on_click)
        app.refreshables.append(self)

    def move(self, k):
        self.y, self.m = shift_month(self.y, self.m, k)
        self.draw()

    def today(self):
        t = dt.date.today()
        self.y, self.m = t.year, t.month
        self.draw()

    def set_month(self, y, m):
        self.y, self.m = y, m
        self.draw()

    def refresh(self):
        self.draw()

    def on_click(self, e):
        for x0, y0, x1, y1, d in self.hit:
            if x0 <= e.x < x1 and y0 <= e.y < y1:
                DayDialog(self.app, d)
                return

    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hit = []
        w, h = cv.winfo_width(), cv.winfo_height()
        self.title.config(text=f"{self.y}년 {self.m}월")
        if w < 80 or h < 80:
            return
        app = self.app
        weeks = calendar.Calendar(6).monthdatescalendar(self.y, self.m)
        evs = events_between(app.store, weeks[0][0], weeks[-1][-1])
        hh = 26
        rh = (h - hh) / len(weeks)
        cw = w / 7
        today = dt.date.today()
        for j, n in enumerate(WD_SUN):
            cv.create_rectangle(j * cw, 0, (j + 1) * cw, hh, fill="#eceff3", outline=C["line"])
            cv.create_text(j * cw + cw / 2, hh / 2, text=n, font=app.font_b,
                           fill=C["red"] if j == 0 else C["blue"] if j == 6 else C["text"])
        lane_h = 17
        for i, week in enumerate(weeks):
            y0 = hh + i * rh
            for j, d in enumerate(week):
                x0 = j * cw
                hn = holiday_name(d)
                off = d.weekday() >= 5 or bool(hn)
                bg = "#eef3fd" if d == today else ("#f7f7f8" if d.month != self.m else ("#fcfcfc" if off else "#ffffff"))
                cv.create_rectangle(x0, y0, x0 + cw, y0 + rh, fill=bg, outline=C["line"])
                col = C["red"] if (d.weekday() == 6 or hn) else C["blue"] if d.weekday() == 5 else C["text"]
                if d.month != self.m:
                    col = C["gray"]
                cv.create_text(x0 + 6, y0 + 4, text=str(d.day), anchor="nw", fill=col, font=app.font_b)
                if hn:
                    cv.create_text(x0 + cw - 4, y0 + 6, text=hn[:7], anchor="ne", fill=C["red"], font=app.font_xs)
                self.hit.append((x0, y0, x0 + cw, y0 + rh, d))
            ws, we = week[0], week[-1]
            segs = [e for e in evs if not (e.end < ws or e.start > we)]
            segs.sort(key=lambda e: (e.start, -(e.end - e.start).days, e.kind))
            lanes, hidden = [], [0] * 7
            max_lane = max(0, int((rh - 24) // lane_h))
            for e in segs:
                cs, ce = max((e.start - ws).days, 0), min((e.end - ws).days, 6)
                lane = next((k for k, last in enumerate(lanes) if last < cs), None)
                if lane is None:
                    lanes.append(ce)
                    lane = len(lanes) - 1
                else:
                    lanes[lane] = ce
                if lane >= max_lane:
                    for c in range(cs, ce + 1):
                        hidden[c] += 1
                    continue
                x0, x1 = cs * cw + 2, (ce + 1) * cw - 2
                y = y0 + 24 + lane * lane_h
                bgc, bgp, fgc = KIND_STYLE[e.kind]
                cv.create_rectangle(x0, y, x1, y + lane_h - 2, fill=bgp if e.start != e.end else bgc, outline="")
                label = e.title
                if e.start < ws:
                    label = "◀ " + label
                if e.end > we:
                    label += " ▶"
                maxch = max(int((x1 - x0 - 8) / 10), 1)
                if len(label) > maxch:
                    label = label[:max(maxch - 1, 1)] + "…"
                cv.create_text(x0 + 4, y + (lane_h - 2) / 2, text=label, anchor="w", fill=fgc, font=app.font_xs)
            for c in range(7):
                if hidden[c]:
                    cv.create_text((c + 1) * cw - 5, y0 + rh - 3, text=f"+{hidden[c]}", anchor="se",
                                   fill=C["sub"], font=app.font_xs)


class DayDialog(tk.Toplevel):
    def __init__(self, app, d):
        super().__init__(app.root)
        self.app, self.d = app, d
        self.title(f"{d:%Y-%m-%d} 일정")
        self.transient(app.root)
        self.configure(bg=C["bg"], padx=12, pady=10)
        hn = holiday_name(d)
        tk.Label(self, text=f"{d:%Y년 %m월 %d일} ({WD[d.weekday()]})" + (f"  · {hn}" if hn else ""),
                 bg=C["bg"], font=app.font_title, fg=C["red"] if hn else C["text"]).pack(anchor="w")
        lb = tk.Listbox(self, width=52, height=10, relief="solid", bd=1, font=app.font, activestyle="none")
        lb.pack(pady=8, fill="both", expand=True)
        evs = events_between(app.store, d, d)
        for e in evs:
            span = f"  ({e.start:%m/%d}~{e.end:%m/%d})" if e.start != e.end else ""
            lb.insert("end", f"{KIND_TAG[e.kind]} {e.title}{span}")
        if not evs:
            lb.insert("end", "일정이 없습니다.")
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x")
        self.ent = tk.Entry(row, relief="solid", bd=1, font=app.font)
        self.ent.pack(side="left", fill="x", expand=True, ipady=3)
        self.ent.bind("<Return>", lambda e: self.add())
        make_btn(row, "할 일 추가", self.add, accent=True).pack(side="left", padx=(6, 0))
        self.ent.focus_set()

    def add(self):
        text = self.ent.get().strip()
        if not text:
            return
        st = self.app.store
        st.d["todos"].append({"id": st.nid(), "text": text, "date": iso(self.d), "done": False})
        st.save()
        self.app.refresh_all()
        self.destroy()


class HolidayDialog(tk.Toplevel):
    """임시공휴일·회사 휴무일 등 직접 추가."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("휴일 추가")
        self.transient(app.root)
        self.configure(bg=C["bg"], padx=12, pady=10)
        tk.Label(self, text="기본 공휴일(대체공휴일 포함)은 자동 반영됩니다.\n임시공휴일·회사 휴무일만 추가하세요.",
                 bg=C["bg"], fg=C["sub"], justify="left").pack(anchor="w")
        self.lb = tk.Listbox(self, width=36, height=8, relief="solid", bd=1, font=app.font)
        self.lb.pack(pady=8)
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x")
        self.d = tk.Entry(row, width=12, relief="solid", bd=1)
        self.d.pack(side="left", ipady=3)
        self.n = tk.Entry(row, width=12, relief="solid", bd=1)
        self.n.pack(side="left", padx=4, ipady=3)
        make_btn(row, "추가", self.add, accent=True, small=True).pack(side="left")
        tk.Label(self, text="날짜 예: 2026-10-02 또는 10-02  /  이름은 선택", bg=C["bg"], fg=C["sub"],
                 font=app.font_s).pack(anchor="w", pady=(2, 6))
        make_btn(self, "선택 삭제", self.remove, small=True).pack(anchor="e")
        self.fill()

    def fill(self):
        self.lb.delete(0, "end")
        for it in sorted(self.app.store.d["extra_off"], key=lambda x: x["date"]):
            self.lb.insert("end", f'{it["date"]}  {it.get("name", "")}')

    def add(self):
        try:
            d = parse_date(self.d.get())
        except ValueError:
            d = None
        if not d:
            messagebox.showwarning("날짜 확인", "날짜 형식을 확인해 주세요.", parent=self)
            return
        ex = self.app.store.d["extra_off"]
        ex[:] = [x for x in ex if x["date"] != iso(d)]
        ex.append({"date": iso(d), "name": self.n.get().strip() or "휴일"})
        self.commit()

    def remove(self):
        sel = self.lb.curselection()
        if not sel:
            return
        key = self.lb.get(sel[0]).split()[0]
        ex = self.app.store.d["extra_off"]
        ex[:] = [x for x in ex if x["date"] != key]
        self.commit()

    def commit(self):
        self.app.store.sync_extra()
        self.app.store.save()
        self.fill()
        self.app.refresh_all()


class RuleManager(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("반복 업무 관리")
        self.transient(app.root)
        self.configure(bg=C["bg"], padx=12, pady=10)
        tk.Label(self, text="매월 반복되는 업무를 등록하면 달력에 자동 표시됩니다.", bg=C["bg"], fg=C["sub"]).pack(anchor="w")
        self.lb = tk.Listbox(self, width=64, height=12, relief="solid", bd=1, font=app.font, activestyle="none")
        self.lb.pack(pady=8, fill="both", expand=True)
        self.lb.bind("<Double-1>", lambda e: self.edit())
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x")
        make_btn(row, "추가", self.add, accent=True).pack(side="left")
        make_btn(row, "수정", self.edit).pack(side="left", padx=6)
        make_btn(row, "삭제", self.remove).pack(side="left")
        self.fill()

    def fill(self):
        self.lb.delete(0, "end")
        for r in self.app.store.d["rules"]:
            t = (r.get("time") + " " if r.get("time") else "")
            self.lb.insert("end", f'{t}{r["title"]}   —   {describe_rule(r)}')

    def add(self):
        RuleEditor(self.app, None, self.fill)

    def _sel(self):
        s = self.lb.curselection()
        return self.app.store.d["rules"][s[0]] if s else None

    def edit(self):
        r = self._sel()
        if r:
            RuleEditor(self.app, r, self.fill)

    def remove(self):
        r = self._sel()
        if r and messagebox.askyesno("삭제", f'"{r["title"]}" 규칙을 삭제할까요?', parent=self):
            self.app.store.d["rules"].remove(r)
            self.app.store.save()
            self.fill()
            self.app.refresh_all()


class RuleEditor(tk.Toplevel):
    TYPES = {"매월 N일": "monthly", "월말 마지막 영업일 기준 N영업일 전": "eom", "매월 기간 (시작일~종료일)": "period"}

    def __init__(self, app, rule, on_done):
        super().__init__(app.root)
        self.app, self.rule, self.on_done = app, rule, on_done
        self.title("반복 업무 수정" if rule else "반복 업무 추가")
        self.transient(app.root)
        self.configure(bg=C["bg"], padx=14, pady=12)
        r = rule or {"title": "", "type": "monthly", "a": 25, "b": 28, "time": ""}
        inv = {v: k for k, v in self.TYPES.items()}
        self.title_v = tk.StringVar(value=r["title"])
        self.type_v = tk.StringVar(value=inv[r["type"]])
        self.a_v, self.b_v = tk.IntVar(value=r["a"]), tk.IntVar(value=r.get("b", 1))
        self.time_v = tk.StringVar(value=r.get("time", ""))
        g = dict(sticky="w", pady=4)
        tk.Label(self, text="업무명", bg=C["bg"]).grid(row=0, column=0, **g)
        tk.Entry(self, textvariable=self.title_v, width=34, relief="solid", bd=1).grid(row=0, column=1, columnspan=2, **g)
        tk.Label(self, text="반복 방식", bg=C["bg"]).grid(row=1, column=0, **g)
        cb = ttk.Combobox(self, textvariable=self.type_v, values=list(self.TYPES), state="readonly", width=32)
        cb.grid(row=1, column=1, columnspan=2, **g)
        cb.bind("<<ComboboxSelected>>", lambda e: self.relabel())
        self.a_lb = tk.Label(self, bg=C["bg"])
        self.a_lb.grid(row=2, column=0, **g)
        self.a_sp = ttk.Spinbox(self, from_=0, to=31, textvariable=self.a_v, width=6)
        self.a_sp.grid(row=2, column=1, **g)
        self.b_lb = tk.Label(self, bg=C["bg"])
        self.b_lb.grid(row=3, column=0, **g)
        self.b_sp = ttk.Spinbox(self, from_=1, to=31, textvariable=self.b_v, width=6)
        self.b_sp.grid(row=3, column=1, **g)
        tk.Label(self, text="시간 (선택)", bg=C["bg"]).grid(row=4, column=0, **g)
        tk.Entry(self, textvariable=self.time_v, width=8, relief="solid", bd=1).grid(row=4, column=1, **g)
        tk.Label(self, text="예: 09:30", bg=C["bg"], fg=C["sub"]).grid(row=4, column=2, sticky="w")
        self.hint = tk.Label(self, bg=C["bg"], fg=C["sub"], justify="left", wraplength=340)
        self.hint.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 8))
        row = tk.Frame(self, bg=C["bg"])
        row.grid(row=6, column=0, columnspan=3, sticky="e")
        make_btn(row, "저장", self.save, accent=True).pack(side="left")
        make_btn(row, "취소", self.destroy).pack(side="left", padx=6)
        self.relabel()
        self.grab_set()

    def relabel(self):
        t = self.TYPES[self.type_v.get()]
        if t == "monthly":
            self.a_lb.config(text="날짜(일)")
            self.b_lb.config(text="")
            self.b_sp.state(["disabled"])
            self.hint.config(text="매월 N일이 주말·공휴일이면 직전 평일에 표시됩니다.")
        elif t == "eom":
            self.a_lb.config(text="몇 영업일 전")
            self.b_lb.config(text="")
            self.b_sp.state(["disabled"])
            self.hint.config(text="0 = 월말 마지막 영업일, 1 = 그 전 영업일.\n말일이 휴일이면 자동으로 앞 영업일 기준이 됩니다.")
        else:
            self.a_lb.config(text="시작일(일)")
            self.b_lb.config(text="종료일(일)")
            self.b_sp.state(["!disabled"])
            self.hint.config(text="종료일이 주말·공휴일이면 직전 평일까지만 기간이 잡힙니다.\n종료일이 시작일보다 작으면 다음 달로 넘어갑니다.")

    def save(self):
        title = self.title_v.get().strip()
        if not title:
            messagebox.showwarning("확인", "업무명을 입력해 주세요.", parent=self)
            return
        t = self.TYPES[self.type_v.get()]
        try:
            a, b = int(self.a_v.get()), int(self.b_v.get())
        except (tk.TclError, ValueError):
            messagebox.showwarning("확인", "숫자를 확인해 주세요.", parent=self)
            return
        tm = self.time_v.get().strip()
        if tm and not re.fullmatch(r"\d{1,2}:\d{2}", tm):
            messagebox.showwarning("확인", "시간은 09:30 형식으로 입력해 주세요.", parent=self)
            return
        if t in ("monthly", "period") and not (1 <= a <= 31):
            messagebox.showwarning("확인", "날짜는 1~31 사이로 입력해 주세요.", parent=self)
            return
        st = self.app.store
        data = {"title": title, "type": t, "a": a, "b": b, "time": tm}
        if self.rule:
            self.rule.update(data)
        else:
            st.d["rules"].append({"id": st.nid(), **data})
        st.save()
        self.on_done()
        self.app.refresh_all()
        self.destroy()


# ─────────────────────────────────────────────────────────────
# 진행건
# ─────────────────────────────────────────────────────────────
class CaseDialog(tk.Toplevel):
    def __init__(self, app, case):
        super().__init__(app.root)
        self.app, self.case = app, case
        self.title("진행건 수정")
        self.transient(app.root)
        self.configure(bg=C["bg"], padx=14, pady=12)
        self.v = {k: tk.StringVar(value=case.get(k, "")) for k in ("cat", "company", "title", "start", "due", "note")}
        labels = (("구분", "cat"), ("업체명", "company"), ("업무내용", "title"), ("시작일", "start"),
                  ("마감일", "due"), ("비고", "note"))
        for i, (lab, k) in enumerate(labels):
            tk.Label(self, text=lab, bg=C["bg"]).grid(row=i, column=0, sticky="w", pady=4)
            if k == "cat":
                w = ttk.Combobox(self, textvariable=self.v[k], values=app.store.d["cats"], width=30)
            else:
                w = tk.Entry(self, textvariable=self.v[k], width=34, relief="solid", bd=1)
            w.grid(row=i, column=1, sticky="w", pady=4)
        self.adj = tk.BooleanVar(value=case.get("adjust", True))
        self.done = tk.BooleanVar(value=case.get("done", False))
        tk.Checkbutton(self, text="마감일이 주말·공휴일이면 직전 평일로 자동 조정", variable=self.adj,
                       bg=C["bg"], activebackground=C["bg"]).grid(row=6, column=0, columnspan=2, sticky="w")
        tk.Checkbutton(self, text="완료 처리", variable=self.done, bg=C["bg"], activebackground=C["bg"]).grid(
            row=7, column=0, columnspan=2, sticky="w")
        row = tk.Frame(self, bg=C["bg"])
        row.grid(row=8, column=0, columnspan=2, sticky="e", pady=(10, 0))
        make_btn(row, "저장", self.save, accent=True).pack(side="left")
        make_btn(row, "취소", self.destroy).pack(side="left", padx=6)
        self.grab_set()

    def save(self):
        company = self.v["company"].get().strip()
        if not company:
            messagebox.showwarning("확인", "업체명은 필수입니다.", parent=self)
            return
        try:
            s, d = parse_date(self.v["start"].get()), parse_date(self.v["due"].get())
        except ValueError:
            messagebox.showwarning("확인", "날짜 형식을 확인해 주세요. (예: 2026-10-05, 10-05)", parent=self)
            return
        c = self.case
        c.update(cat=self.v["cat"].get().strip(), company=company, title=self.v["title"].get().strip(),
                 start=iso(s), due=iso(d), note=self.v["note"].get().strip(), adjust=self.adj.get())
        was = c.get("done", False)
        c["done"] = self.done.get()
        if c["done"] and not was:
            c["done_at"] = iso(dt.date.today())
        if not c["done"]:
            c["done_at"] = ""
        cats = self.app.store.d["cats"]
        if c["cat"] and c["cat"] not in cats:
            cats.append(c["cat"])
        self.app.store.save()
        self.app.refresh_all()
        self.destroy()


class CaseTable(tk.Frame):
    COLS = (("cat", "구분", 70), ("company", "업체명", 140), ("title", "업무내용", 230), ("start", "시작일", 90),
            ("due", "마감일", 120), ("status", "상태", 60), ("note", "비고", 200))

    def __init__(self, parent, app, show_done, searchable=False):
        super().__init__(parent, bg=C["bg"])
        self.app, self.show_done, self.table = app, show_done, self
        self.q = tk.StringVar()
        if searchable:
            bar = tk.Frame(self, bg=C["bg"])
            bar.pack(fill="x", padx=6, pady=(8, 2))
            tk.Label(bar, text="검색", bg=C["bg"], fg=C["sub"]).pack(side="left")
            e = tk.Entry(bar, textvariable=self.q, relief="solid", bd=1)
            e.pack(side="left", fill="x", expand=True, padx=6, ipady=3)
            self.q.trace_add("write", lambda *a: self.refresh())
        wrap = tk.Frame(self, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree = ttk.Treeview(wrap, columns=[c[0] for c in self.COLS], show="headings", selectmode="extended")
        for k, name, w in self.COLS:
            self.tree.heading(k, text=name)
            self.tree.column(k, width=w, anchor="w", stretch=k in ("title", "note"))
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("over", foreground=C["red"])
        self.tree.tag_configure("soon", foreground=C["warn"])
        self.tree.tag_configure("done", foreground=C["gray"])
        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<Button-3>", self.on_right)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="수정", command=self.edit_selected)
        self.menu.add_command(label="완료 / 진행중 전환", command=self.toggle_selected)
        self.menu.add_separator()
        self.menu.add_command(label="삭제", command=self.delete_selected)
        app.refreshables.append(self)

    def refresh(self):
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        today = dt.date.today()
        q = self.q.get().strip().lower()
        cases = [c for c in self.app.store.d["cases"] if self.show_done or not c.get("done")]
        if q:
            cases = [c for c in cases if q in " ".join(str(c.get(k, "")) for k in ("cat", "company", "title", "note")).lower()]
        cases.sort(key=lambda c: (bool(c.get("done")), iso(case_end(c)) or "9999-12-31"))
        for c in cases:
            s, e = case_span(c)
            raw = from_iso(c.get("due"))
            due_txt = fmt_d(e) if c.get("due") else ""
            if raw and e and raw != e and c.get("adjust", True):
                due_txt += " ←조정"
            tag = ""
            if c.get("done"):
                tag = "done"
            elif e and e < today:
                tag = "over"
            elif e and (e - today).days <= 2:
                tag = "soon"
            self.tree.insert("", "end", iid=str(c["id"]), tags=(tag,) if tag else (), values=(
                c.get("cat", ""), c.get("company", ""), c.get("title", ""), fmt_d(from_iso(c.get("start"))),
                due_txt, "완료" if c.get("done") else "진행", c.get("note", "")))
        for iid in sel:
            if self.tree.exists(iid):
                self.tree.selection_add(iid)

    def _cases(self):
        ids = {int(i) for i in self.tree.selection()}
        return [c for c in self.app.store.d["cases"] if c["id"] in ids]

    def on_double(self, e):
        if self.tree.identify_row(e.y):
            self.edit_selected()

    def on_right(self, e):
        iid = self.tree.identify_row(e.y)
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            self.menu.tk_popup(e.x_root, e.y_root)

    def edit_selected(self):
        cs = self._cases()
        if cs:
            CaseDialog(self.app, cs[0])

    def toggle_selected(self):
        for c in self._cases():
            c["done"] = not c.get("done")
            c["done_at"] = iso(dt.date.today()) if c["done"] else ""
        self.app.store.save()
        self.app.refresh_all()

    def delete_selected(self):
        cs = self._cases()
        if not cs:
            messagebox.showinfo("선택 삭제", "삭제할 항목을 먼저 선택해 주세요.")
            return
        if messagebox.askyesno("선택 삭제", f"선택한 {len(cs)}건을 삭제할까요?"):
            for c in cs:
                self.app.store.d["cases"].remove(c)
            self.app.store.save()
            self.app.refresh_all()


class StatsView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.text = tk.Text(self, relief="flat", bg="#fff", font=app.font, padx=16, pady=12, state="disabled",
                            highlightthickness=1, highlightbackground=C["line"])
        self.text.pack(fill="both", expand=True, padx=6, pady=6)
        app.refreshables.append(self)

    def refresh(self):
        st = self.app.store
        today = dt.date.today()
        cs = st.d["cases"]
        act = [c for c in cs if not c.get("done")]
        over = [c for c in act if case_end(c) and case_end(c) < today]
        soon = [c for c in act if case_end(c) and 0 <= (case_end(c) - today).days <= 3]
        mon = f"{today:%Y-%m}"
        reg = sum(1 for c in cs if c.get("created", "").startswith(mon))
        comp = sum(1 for c in cs if c.get("done_at", "").startswith(mon))
        lines = [f"전체 {len(cs)}건   ·   진행 {len(act)}건   ·   완료 {len(cs) - len(act)}건", "",
                 f"지연(마감 지남) {len(over)}건   ·   3일 내 마감 {len(soon)}건", "",
                 f"이번 달({today:%Y-%m})  등록 {reg}건   ·   완료 {comp}건", "", "[구분별]"]
        cats = {}
        for c in cs:
            k = c.get("cat") or "(미분류)"
            a = cats.setdefault(k, [0, 0])
            a[1 if c.get("done") else 0] += 1
        for k, (a, b) in sorted(cats.items()):
            lines.append(f"  {k}   진행 {a} / 완료 {b}")
        cnt = {}
        for c in act:
            cnt[c.get("company", "")] = cnt.get(c.get("company", ""), 0) + 1
        lines += ["", "[업체별 진행건 TOP 5]"]
        for k, v in sorted(cnt.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {k}   {v}건")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(lines))
        self.text.config(state="disabled")


class TodaySummary(tk.Frame):
    """미니창 상단 '오늘 현황'."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        tk.Label(self, text="오늘 현황", bg=C["panel"], font=app.font_b).pack(anchor="w", padx=8, pady=(6, 0))
        self.lb = tk.Label(self, bg=C["panel"], fg=C["text"], justify="left", anchor="w", wraplength=270, font=app.font_s)
        self.lb.pack(fill="x", padx=8, pady=(2, 8))
        self.app = app
        app.refreshables.append(self)

    def refresh(self):
        st, t = self.app.store, dt.date.today()
        evs = events_between(st, t, t)
        due = [e for e in evs if e.kind == "case" and e.end == t]
        ongoing = [e for e in evs if e.kind == "case" and e.end != t]
        rules = [e for e in evs if e.kind == "rule"]
        lines = [f"마감 {len(due)}건 · 진행 중 기간 {len(ongoing)}건 · 지연 {overdue_count(st)}건 · 반복 {len(rules)}건"]
        if is_off(t):
            lines.append(f"오늘은 휴일입니다{' (' + holiday_name(t) + ')' if holiday_name(t) else ''}")
        for tag, group in (("마감", due), ("반복", rules)):
            for e in group[:5]:
                lines.append(f"• [{tag}] {e.title}")
        self.lb.config(text="\n".join(lines))


# ─────────────────────────────────────────────────────────────
# 앱
# ─────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        try:  # 윈도우 고해상도 흐림 방지
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.root = tk.Tk()
        self.root.title("WORK SPACE")
        self.store = Store(DATA_PATH)
        self.memos, self.refreshables = [], []
        fams = set(tkfont.families())
        ff = "맑은 고딕" if "맑은 고딕" in fams else "Malgun Gothic" if "Malgun Gothic" in fams else \
            tkfont.nametofont("TkDefaultFont").actual("family")
        self.font = tkfont.Font(family=ff, size=10)
        self.font_b = tkfont.Font(family=ff, size=10, weight="bold")
        self.font_s = tkfont.Font(family=ff, size=9)
        self.font_sb = tkfont.Font(family=ff, size=9, weight="bold")
        self.font_xs = tkfont.Font(family=ff, size=8)
        self.font_title = tkfont.Font(family=ff, size=13, weight="bold")
        self.font_done = tkfont.Font(family=ff, size=10, overstrike=True)
        self.root.option_add("*Font", self.font)
        self.root.option_add("*TCombobox*Listbox.font", self.font)
        self.root.configure(bg=C["bg"])
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Treeview", rowheight=26, font=self.font, background="#fff", fieldbackground="#fff",
                     bordercolor=C["line"])
        st.configure("Treeview.Heading", font=self.font_b, background="#eceff3", relief="flat")
        st.map("Treeview", background=[("selected", C["accent_bg"])], foreground=[("selected", C["text"])])
        st.configure("TNotebook", background=C["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", padding=(16, 7), font=self.font)
        st.map("TNotebook.Tab", background=[("selected", "#fff")], foreground=[("selected", C["accent"])])
        self.root.bind_all("<MouseWheel>", self._wheel)
        self.today = dt.date.today()
        self.build_main()
        self.build_mini()
        self.refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.after(60000, self.tick)
        if not HAS_HOLIDAYS:
            self.root.after(500, lambda: messagebox.showwarning(
                "공휴일 라이브러리 없음",
                "holidays 라이브러리가 없어 양력 고정 공휴일만 반영됩니다.\n(설/추석/대체공휴일 미반영)\n"
                "pip install holidays 후 다시 실행하세요."))

    # ── 공통 동작
    def _wheel(self, e):
        w = e.widget
        while isinstance(w, tk.Misc):
            if isinstance(w, (tk.Text, ttk.Treeview, tk.Listbox)):
                return
            if isinstance(w, ScrollFrame):
                w.cv.yview_scroll(int(-e.delta / 120), "units")
                return
            w = w.master

    def refresh_all(self):
        for p in list(self.refreshables):
            try:
                p.refresh()
            except tk.TclError:
                pass

    def sync_memos(self, source):
        for m in self.memos:
            if m is not source and m.key == source.key:
                m.sync()

    def tick(self):
        if dt.date.today() != self.today:
            self.today = dt.date.today()
            self.refresh_all()
        self.root.after(60000, self.tick)

    def goto(self, d):
        self.cal.set_month(d.year, d.month)
        self.nb.select(self.cal)
        DayDialog(self, d)

    # ── 메인창
    def build_main(self):
        r = self.root
        geo = self.store.d["geo"].get("main") or "1280x780"
        r.geometry(geo)
        r.minsize(1000, 640)
        r.columnconfigure(0, weight=1)
        r.rowconfigure(2, weight=1)
        bar = tk.Frame(r, bg=C["bg"])
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        tk.Label(bar, text="WORK SPACE", bg=C["bg"], fg=C["accent"], font=self.font_title).pack(side="left")
        make_btn(bar, "선택 삭제", self.delete_current, small=True).pack(side="right")
        make_btn(bar, "새로고침", self.refresh_all, small=True).pack(side="right", padx=6)
        make_btn(bar, "미니창", self.toggle_mini, small=True).pack(side="right")
        memo = MemoBox(r, self, "memo", "업무 참고 메모 (자동 저장)", 4)
        memo.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        body = tk.Frame(r, bg=C["bg"])
        body.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 10))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=C["bg"], width=290)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        left.grid_propagate(False)
        left.rowconfigure(1, weight=1)
        MiniCal(left, self).grid(row=0, column=0, sticky="ew")
        TodoPanel(left, self, wrap=190).grid(row=1, column=0, sticky="nsew", pady=6)
        MemoBox(left, self, "notepad", "메모장", 6).grid(row=2, column=0, sticky="ew")
        right = tk.Frame(body, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self.build_input(right).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.nb = ttk.Notebook(right)
        self.nb.grid(row=1, column=0, sticky="nsew")
        t1 = CaseTable(self.nb, self, show_done=False)
        t2 = CaseTable(self.nb, self, show_done=True, searchable=True)
        self.cal = CalendarView(self.nb, self)
        stats = StatsView(self.nb, self)
        self.nb.add(t1, text="진행건 관리")
        self.nb.add(t2, text="전체 조회 (마감 포함)")
        self.nb.add(self.cal, text="업무 달력")
        self.nb.add(stats, text="통계")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

    def build_input(self, parent):
        f = tk.Frame(parent, bg=C["panel"], highlightbackground=C["line"], highlightthickness=1)
        self.nv = {k: tk.StringVar() for k in ("cat", "company", "title", "start", "due", "note")}
        spec = (("cat", "구분", 9), ("company", "업체명 (필수)", 16), ("title", "업무내용", 26),
                ("start", "시작일 (예 10-05)", 12), ("due", "마감일 (예 10-20)", 12), ("note", "비고", 18))
        for i, (k, cap, w) in enumerate(spec):
            tk.Label(f, text=cap, bg=C["panel"], fg=C["sub"], font=self.font_xs).grid(row=0, column=i, sticky="w", padx=(8, 0), pady=(6, 0))
            if k == "cat":
                self.cat_cb = ttk.Combobox(f, textvariable=self.nv[k], values=self.store.d["cats"], width=w)
                self.cat_cb.grid(row=1, column=i, padx=(8, 0), pady=(0, 8), ipady=2)
                self.cat_cb.bind("<Return>", lambda e: self.add_case())
            else:
                e = tk.Entry(f, textvariable=self.nv[k], width=w, relief="solid", bd=1)
                e.grid(row=1, column=i, padx=(8, 0), pady=(0, 8), ipady=3)
                e.bind("<Return>", lambda ev: self.add_case())
        make_btn(f, "+ 신규 등록", self.add_case, accent=True).grid(row=1, column=len(spec), padx=8, pady=(0, 8))
        return f

    def add_case(self):
        v = {k: x.get().strip() for k, x in self.nv.items()}
        if not v["company"]:
            messagebox.showwarning("확인", "업체명은 필수입니다.")
            return
        try:
            s, d = parse_date(v["start"]), parse_date(v["due"])
        except ValueError:
            messagebox.showwarning("확인", "날짜 형식을 확인해 주세요. (예: 2026-10-05, 10-05, 1005)")
            return
        st = self.store
        st.d["cases"].append({"id": st.nid(), "cat": v["cat"], "company": v["company"], "title": v["title"],
                              "start": iso(s), "due": iso(d), "note": v["note"], "adjust": True,
                              "done": False, "done_at": "", "created": iso(dt.date.today())})
        if v["cat"] and v["cat"] not in st.d["cats"]:
            st.d["cats"].append(v["cat"])
            self.cat_cb.config(values=st.d["cats"])
        for k in ("company", "title", "start", "due", "note"):
            self.nv[k].set("")
        st.save()
        self.refresh_all()

    def delete_current(self):
        w = self.nb.nametowidget(self.nb.select())
        t = getattr(w, "table", None)
        if t:
            t.delete_selected()
        else:
            messagebox.showinfo("선택 삭제", "진행건 목록에서 항목을 선택한 뒤 사용해 주세요.")

    # ── 미니창
    def build_mini(self):
        m = self.mini = tk.Toplevel(self.root)
        m.title("WORK SPACE MINI")
        m.geometry(self.store.d["geo"].get("mini") or "320x640")
        m.minsize(280, 420)
        m.configure(bg=C["bg"])
        m.attributes("-topmost", True)
        m.protocol("WM_DELETE_WINDOW", m.withdraw)
        top = tk.Frame(m, bg=C["bg"])
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="WORK SPACE MINI", bg=C["bg"], fg=C["accent"], font=self.font_b).pack(side="left")
        self.pin = tk.BooleanVar(value=True)
        tk.Checkbutton(top, text="항상 위", variable=self.pin, bg=C["bg"], activebackground=C["bg"], font=self.font_s,
                       command=lambda: m.attributes("-topmost", self.pin.get())).pack(side="right")
        TodaySummary(m, self).pack(fill="x", padx=8, pady=4)
        TodoPanel(m, self, wrap=230).pack(fill="both", expand=True, padx=8, pady=4)
        MemoBox(m, self, "notepad", "메모장", 5).pack(fill="x", padx=8, pady=(4, 8))

    def toggle_mini(self):
        if self.mini.state() == "withdrawn":
            self.mini.deiconify()
            self.mini.lift()
        else:
            self.mini.withdraw()

    def quit(self):
        for m in self.memos:
            m._flush()
        try:
            self.store.d["geo"] = {"main": self.root.geometry(), "mini": self.mini.geometry()}
        except tk.TclError:
            pass
        self.store.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
