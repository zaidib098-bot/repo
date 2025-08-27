import os, shutil, threading
import flet as ft
import socket
# توافق الأيقونات
if hasattr(ft, "icons"):
    ICONS = ft.icons
elif hasattr(ft, "Icons"):
    ICONS = ft.Icons
else:
    raise RuntimeError("Flet icons API not found")

from backend.db import init_db
from backend.auth import verify_login
from backend import models as m
from backend.qr_utils import decode_qr_from_image, decode_qr_from_camera
from common_ui import login_view

PRIMARY = "#1f6aa5"   # لون قريب من الشعار
APPBAR_BG = "#eef7ff"
LOGO_PATH = "assets/logo.png"
COLLEGES = ["الهندسة", "الطب", "الصيدلة", "الحقوق"]

def main(page: ft.Page):
    page.title = "جامعة الرشيد - الطالب"
    page.theme = ft.Theme(color_scheme_seed=PRIMARY)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 420
    page.window_height = 820
    page.scroll = ft.ScrollMode.AUTO
    init_db()

    current_user = {"user": None}
    content_container = ft.Container()

    # ---------- الأقسام ----------
    def make_home():
        u = current_user["user"]
        completed = m.compute_completed_credits(u["id"])
        info = [
            ft.Text(f"الاسم: {u.get('full_name') or ''}", size=18),
            ft.Text(f"الرقم الجامعي: {u.get('uni_id') or '-'}", size=18),
            ft.Text(f"المستوى: {u.get('level') or '-'}", size=18),
            ft.Text(f"المعدل: {u.get('gpa') if u.get('gpa') is not None else '-'}", size=18),
            ft.Text(f"الساعات المنجزة: {completed}", size=18),
        ]
        return ft.Column([ft.Text("الملف الشخصي", size=20, weight=ft.FontWeight.BOLD)] + info, spacing=8)

    def make_register_courses():
        all_courses = m.list_courses()
        enrolled_rows = m.list_enrollments(current_user['user']['id'])
        enrolled = {r['course_id'] for r in enrolled_rows}
        checks = []
        for c in all_courses:
            ch = ft.Checkbox(label=f"{c['code']} - {c['name']}", value=c['id'] in enrolled)
            ch.data = c['id']
            checks.append(ch)
        msg = ft.Text()
        def save(_e):
            user_id = current_user['user']['id']
            for ch in checks:
                if ch.value and ch.data not in enrolled:
                    m.enroll_course(user_id, ch.data)
                if (not ch.value) and ch.data in enrolled:
                    m.delete_enrollment(user_id, ch.data)
            msg.value = "تم حفظ التسجيل/الحذف."
            page.update()
        return ft.Column([
            ft.Text("تسجيل/حذف المقررات", size=20, weight=ft.FontWeight.BOLD),
            ft.Column(checks, scroll=ft.ScrollMode.AUTO, height=320),
            ft.ElevatedButton("حفظ", on_click=save),
            msg
        ], spacing=10)

    def make_exam_schedule():
        rows = m.list_exams_for_student(current_user['user']['id'])
        items = [ft.DataRow(cells=[
            ft.DataCell(ft.Text(r['code'])), ft.DataCell(ft.Text(r['name'])),
            ft.DataCell(ft.Text(r['exam_date'])), ft.DataCell(ft.Text(r['start_time'])),
            ft.DataCell(ft.Text(r['room'] or "-")),
        ]) for r in rows]
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("رمز")), ft.DataColumn(ft.Text("مقرر")),
                                      ft.DataColumn(ft.Text("تاريخ")), ft.DataColumn(ft.Text("ساعة")),
                                      ft.DataColumn(ft.Text("قاعة"))], rows=items)
        return ft.Column([ft.Text("برنامج الامتحان", size=20, weight=ft.FontWeight.BOLD), table], spacing=10)

    def make_timetable():
        rows = m.list_timetable_for_student(current_user['user']['id'])
        items = [ft.DataRow(cells=[
            ft.DataCell(ft.Text(r['day_of_week'])), ft.DataCell(ft.Text(r['code'])),
            ft.DataCell(ft.Text(r['name'])), ft.DataCell(ft.Text(f"{r['start_time']} - {r['end_time']}")),
            ft.DataCell(ft.Text(r['room'] or "-")),
        ]) for r in rows]
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("اليوم")), ft.DataColumn(ft.Text("رمز")),
                                      ft.DataColumn(ft.Text("مقرر")), ft.DataColumn(ft.Text("الوقت")),
                                      ft.DataColumn(ft.Text("قاعة"))], rows=items)
        return ft.Column([ft.Text("البرنامج الدراسي", size=20, weight=ft.FontWeight.BOLD), table], spacing=10)

    def make_grades():
        rows = m.list_grades(current_user['user']['id'])
        items = [ft.DataRow(cells=[
            ft.DataCell(ft.Text(r['code'])), ft.DataCell(ft.Text(r['name'])),
            ft.DataCell(ft.Text(r['exam_type'])), ft.DataCell(ft.Text(str(r['grade']))),
        ]) for r in rows]
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("رمز")), ft.DataColumn(ft.Text("مقرر")),
                                      ft.DataColumn(ft.Text("نوع")), ft.DataColumn(ft.Text("العلامة"))], rows=items)
        return ft.Column([ft.Text("علاماتي", size=20, weight=ft.FontWeight.BOLD), table], spacing=10)

    def make_finance():
        rows = m.list_finance(current_user['user']['id'])
        total_due = sum(r['amount'] for r in rows if not r['paid'])
        items = [ft.DataRow(cells=[
            ft.DataCell(ft.Text(r['description'])), ft.DataCell(ft.Text(str(r['amount']))),
            ft.DataCell(ft.Text(r['due_date'] or "-")), ft.DataCell(ft.Text("نعم" if r['paid'] else "لا")),
        ]) for r in rows]
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("الوصف")), ft.DataColumn(ft.Text("المبلغ")),
                                      ft.DataColumn(ft.Text("الاستحقاق")), ft.DataColumn(ft.Text("مدفوع؟"))], rows=items)
        return ft.Column([ft.Text("المالية", size=20, weight=ft.FontWeight.BOLD), table,
                          ft.Text(f"الإجمالي غير المدفوع: {total_due}")], spacing=10)

    def make_buses():
        rows = m.list_buses()
        items = [ft.DataRow(cells=[
            ft.DataCell(ft.Text(r['route'])), ft.DataCell(ft.Text(r['depart_time'])),
            ft.DataCell(ft.Text(r['origin'])), ft.DataCell(ft.Text(r['destination'])),
        ]) for r in rows]
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("الخط")), ft.DataColumn(ft.Text("انطلاق")),
                                      ft.DataColumn(ft.Text("من")), ft.DataColumn(ft.Text("إلى"))], rows=items)
        return ft.Column([ft.Text("مواعيد باصات الجامعة", size=20, weight=ft.FontWeight.BOLD), table], spacing=10)

    def make_scan_qr():
        picked = ft.Text("")
        result = ft.Text("")
        fp = ft.FilePicker()
        page.overlay.append(fp)

        def scan_via_camera(_e):
            result.value = "جاري فتح الكاميرا..."
            page.update()
            def worker():
                token = decode_qr_from_camera()
                if not token:
                    result.value = "لم يتم قراءة أي QR."
                else:
                    if not token.startswith("LECTURE|"):
                        result.value = "الكود غير صالح."
                    else:
                        lec = m.get_lecture_by_token(token)
                        if not lec:
                            result.value = "المحاضرة غير موجودة."
                        else:
                            ok = m.record_attendance(current_user['user']['id'], lec['id'])
                            result.value = "تم تسجيل الحضور ✅" if ok else "تم تسجيل الحضور مسبقاً."
                page.update()
            threading.Thread(target=worker, daemon=True).start()

        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                result.value = "لم يتم اختيار ملف."
                page.update(); return
            f = e.files[0]
            picked.value = f.name
            token = decode_qr_from_image(f.path)
            if not token or not token.startswith("LECTURE|"):
                result.value = "الكود غير صالح."
            else:
                lec = m.get_lecture_by_token(token)
                if not lec:
                    result.value = "المحاضرة غير موجودة."
                else:
                    ok = m.record_attendance(current_user['user']['id'], lec['id'])
                    result.value = "تم تسجيل الحضور ✅" if ok else "تم تسجيل الحضور مسبقاً."
            page.update()

        fp.on_result = on_file_picked
        return ft.Column([
            ft.Text("تسجيل الحضور - مسح QR", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([ft.ElevatedButton("مسح بالكاميرا", on_click=scan_via_camera),
                    ft.OutlinedButton("اختيار صورة...", on_click=lambda _: fp.pick_files(allow_multiple=False))], spacing=8),
            picked, result
        ], spacing=10)

    def make_college_materials():
        choice = ft.Dropdown(label="اختر الكلية",
                             options=[ft.dropdown.Option(c) for c in COLLEGES],
                             value=COLLEGES[0])
        listview = ft.ListView(expand=True, spacing=8, height=360)
        save_picker = ft.FilePicker()
        page.overlay.append(save_picker)

        def load_list():
            listview.controls.clear()
            files = m.list_college_materials_fs(choice.value)
            if not files:
                listview.controls.append(ft.Text("لا توجد ملفات. ضع ملفات داخل assets/materials/<الكلية>/"))
            for r in files:
                def on_download(_e, src=r['file_path']):
                    save_picker.save_file(file_name=os.path.basename(src))
                    def after_pick(ev: ft.FilePickerResultEvent, s=src):
                        if ev.path:
                            try:
                                shutil.copy(s, ev.path)
                                page.snack_bar = ft.SnackBar(ft.Text("تم التحميل بنجاح")); page.snack_bar.open = True
                                page.update()
                            except Exception as ex:
                                page.snack_bar = ft.SnackBar(ft.Text(f"فشل التحميل: {ex}")); page.snack_bar.open = True
                                page.update()
                    save_picker.on_result = after_pick
                listview.controls.append(
                    ft.Card(content=ft.ListTile(
                        title=ft.Text(r['title']),
                        subtitle=ft.Text(os.path.basename(r['file_path'])),
                        trailing=ft.IconButton(icon=ICONS.DOWNLOAD, tooltip="تحميل", on_click=on_download)
                    ))
                )
            page.update()

        choice.on_change = lambda e: load_list()
        load_list()
        return ft.Column([ft.Text("محاضرات الكليات", size=20, weight=ft.FontWeight.BOLD), choice, listview], spacing=10)

    sections = {
        0: ("الملف", make_home),
        1: ("مسح QR", make_scan_qr),
        2: ("تسجيل المقررات", make_register_courses),
        3: ("برنامج الامتحان", make_exam_schedule),
        4: ("البرنامج الدراسي", make_timetable),
        5: ("العلامات", make_grades),
        6: ("المالية", make_finance),
        7: ("باصات الجامعة", make_buses),
        8: ("محاضرات الكليات", make_college_materials),
    }

    def set_section(i: int):
        title, builder = sections[i]
        content_container.content = ft.Container(builder(), padding=16)
        page.update()

    # ---------- تسجيل الدخول/الخروج ----------
    def on_login(username, password, info_text):
        user = verify_login(username, password)
        if not user:
            info_text.value = "بيانات الدخول غير صحيحة."; page.update(); return
        if user["role"] != "student":
            info_text.value = "هذا التطبيق مخصص للطلاب."; page.update(); return
        current_user["user"] = user
        show_home()

    def do_logout(e=None):
        current_user["user"] = None
        page.views.clear()
        page.views.append(login_view(on_login, "جامعة الرشيد – الطالب"))
        page.update()

    def appbar(title: str):
        logo = ft.Image(src=LOGO_PATH, height=32) if os.path.exists(LOGO_PATH) else None
        return ft.AppBar(title=ft.Text(title), bgcolor=APPBAR_BG, leading=logo,
                         actions=[ft.IconButton(icon=ICONS.LOGOUT, tooltip="تسجيل خروج", on_click=do_logout)])

    def show_home():
        rail = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, group_alignment=-0.9,
            min_width=90, min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(icon=ICONS.PERSON, label="الملف"),
                ft.NavigationRailDestination(icon=ICONS.QR_CODE_SCANNER, label="مسح QR"),
                ft.NavigationRailDestination(icon=ICONS.LIBRARY_ADD, label="تسجيل المقررات"),
                ft.NavigationRailDestination(icon=ICONS.EVENT, label="الامتحان"),
                ft.NavigationRailDestination(icon=ICONS.SCHEDULE, label="البرنامج"),
                ft.NavigationRailDestination(icon=ICONS.SCHOOL, label="العلامات"),
                ft.NavigationRailDestination(icon=ICONS.ACCOUNT_BALANCE_WALLET, label="المالية"),
                ft.NavigationRailDestination(icon=ICONS.DIRECTIONS_BUS, label="الباصات"),
                ft.NavigationRailDestination(icon=ICONS.MENU_BOOK, label="محاضرات الكليات"),
            ],
            on_change=lambda e: set_section(e.control.selected_index)
        )
        page.views.clear()
        page.views.append(
            ft.View(route="/home", appbar=appbar("جامعة الرشيد – الطالب"),
                    controls=[ft.Row([rail, ft.VerticalDivider(width=1),
                                      ft.Container(content_container, expand=True)], expand=True)], padding=0)
        )
        set_section(0); page.update()

    page.views.append(login_view(on_login, "جامعة الرشيد – الطالب"))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)

    if __name__ == "__main__":
    # الحصول على عنوان IP الخاص بالكمبيوتر
     hostname = socket.gethostname()
     ip_address = socket.gethostbyname(hostname)
    
    print("=" * 50)
    print(f"لتشغيل على الهاتف: http://{ip_address}:51500")
    print("أو على الكمبيوتر: http://localhost:51500")
    print("=" * 50)
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    print(f"📍 عنوان IP للاتصال: {ip}")
    ft.app(target=main, port=51500)