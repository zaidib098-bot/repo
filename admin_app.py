import os
import flet as ft

if hasattr(ft, "icons"):
    ICONS = ft.icons
elif hasattr(ft, "Icons"):
    ICONS = ft.Icons
else:
    raise RuntimeError("Flet icons API not found")

from backend.db import init_db, get_conn
from backend.auth import verify_login
from backend import models as m
from backend.qr_utils import generate_qr_png
from common_ui import login_view

PRIMARY = "#1f6aa5"
APPBAR_BG = "#eef7ff"
LOGO_PATH = "assets/logo.png"

def main(page: ft.Page):
    page.title = "جامعة الرشيد - الأدمن"
    page.theme = ft.Theme(color_scheme_seed=PRIMARY)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1150
    page.window_height = 820
    page.scroll = ft.ScrollMode.AUTO
    init_db()

    current_user = {"user": None}
    content_container = ft.Container()

    # ---- الطلاب ----
    def students_section():
        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("اسم المستخدم")),
            ft.DataColumn(ft.Text("الاسم")), ft.DataColumn(ft.Text("الرقم الجامعي")),
            ft.DataColumn(ft.Text("المستوى")), ft.DataColumn(ft.Text("المعدل")),
            ft.DataColumn(ft.Text("إجراءات")),
        ])

        def build_rows():
            table.rows = []
            for s in m.list_students():
                def edit_handler(st=s):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل الطالب #{st['id']}"))
                        full_name = ft.TextField(label="الاسم", value=st.get('full_name') or "")
                        uni_id = ft.TextField(label="الرقم الجامعي", value=st.get('uni_id') or "")
                        level = ft.TextField(label="المستوى", value=st.get('level') or "")
                        gpa = ft.TextField(label="المعدل", value=str(st.get('gpa') or ""))
                        def save(__e):
                            m.update_student(st['id'], full_name=full_name.value, uni_id=uni_id.value,
                                             level=level.value, gpa=float(gpa.value or 0))
                            d.open = False
                            build_rows()
                            page.update()
                        d.content = ft.Column([full_name, uni_id, level, gpa], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open = True; page.update()
                    return _
                def delete_handler(st=s):
                    def _(_e):
                        if hasattr(m, "delete_student"):
                            m.delete_student(st['id'])
                        build_rows(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(s['id']))), ft.DataCell(ft.Text(s['username'])),
                    ft.DataCell(ft.Text(s.get('full_name') or "")),
                    ft.DataCell(ft.Text(s.get('uni_id') or "-")),
                    ft.DataCell(ft.Text(s.get('level') or "-")),
                    ft.DataCell(ft.Text(str(s.get('gpa')) if s.get('gpa') is not None else "-")),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
        build_rows()

        # إنشاء طالب
        username = ft.TextField(label="اسم المستخدم")
        password = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True)
        full_name = ft.TextField(label="الاسم الكامل")
        uni_id = ft.TextField(label="الرقم الجامعي")
        level = ft.TextField(label="المستوى")
        gpa = ft.TextField(label="المعدل", value="0")
        info = ft.Text()

        def create_student(_e):
            if not username.value or not password.value:
                info.value = "الرجاء تعبئة الحقول الأساسية."; page.update(); return
            import secrets, hashlib
            salt = secrets.token_hex(16)
            pwd_hash = hashlib.sha256((salt + password.value).encode("utf-8")).hexdigest()
            try:
                m.add_student(username.value, pwd_hash, salt, full_name.value, uni_id.value, level.value, float(gpa.value or 0))
                info.value = "تم إنشاء الطالب."
                username.value = password.value = full_name.value = uni_id.value = level.value = gpa.value = ""
                build_rows(); page.update()
            except Exception as ex:
                info.value = f"خطأ: {ex}"; page.update()

        form = ft.Column([
            ft.Text("إضافة طالب", size=18, weight=ft.FontWeight.BOLD),
            username, password, full_name, uni_id, level, gpa,
            ft.ElevatedButton("إنشاء", on_click=create_student),
            info
        ], width=320)

        return ft.Row([ft.Container(table, expand=True), ft.VerticalDivider(width=1), form], expand=True)

    # ---- المقررات ----
    def courses_section():
        code = ft.TextField(label="رمز")
        name = ft.TextField(label="اسم")
        credits = ft.TextField(label="ساعات", value="3")
        info = ft.Text()

        def add_course(_e):
            try:
                m.add_course(code.value, name.value, int(credits.value or 3))
                info.value = "تمت إضافة المقرر."; refresh()
            except Exception as ex:
                info.value = f"خطأ: {ex}"
            page.update()

        def build_table():
            dt = ft.DataTable(columns=[
                ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("رمز")),
                ft.DataColumn(ft.Text("اسم")), ft.DataColumn(ft.Text("ساعات")),
                ft.DataColumn(ft.Text("إجراءات")),
            ], rows=[])
            for r in m.list_courses():
                def edit_handler(rr=r):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل مقرر #{rr['id']}"))
                        _code = ft.TextField(label="رمز", value=rr['code'])
                        _name = ft.TextField(label="اسم", value=rr['name'])
                        _cr = ft.TextField(label="ساعات", value=str(rr['credits']))
                        def save(__e):
                            if hasattr(m, "update_course"):
                                m.update_course(rr['id'], code=_code.value, name=_name.value, credits=int(_cr.value or rr['credits']))
                            d.open=False; refresh()
                        d.content = ft.Column([_code, _name, _cr], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open=True; page.update()
                    return _
                def delete_handler(rr=r):
                    def _(_e):
                        if hasattr(m, "delete_course"):
                            m.delete_course(rr['id']); refresh()
                    return _
                dt.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r['id']))), ft.DataCell(ft.Text(r['code'])),
                    ft.DataCell(ft.Text(r['name'])), ft.DataCell(ft.Text(str(r['credits']))),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
            return dt

        def refresh():
            content_container.content = ft.Container(courses_section(), padding=16); page.update()

        table = build_table()
        return ft.Column([
            ft.Text("إدارة المقررات", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([code, name, credits, ft.ElevatedButton("إضافة", on_click=add_course)], spacing=8),
            info, table
        ], spacing=10)

    # ---- المحاضرات & QR ----
    def lectures_section():
        courses = m.list_courses()
        course_dd = ft.Dropdown(label="المقرر", options=[ft.dropdown.Option(str(c['id']), f"{c['code']} - {c['name']}") for c in courses])
        date = ft.TextField(label="تاريخ (YYYY-MM-DD)")
        start = ft.TextField(label="بداية (HH:MM)")
        end = ft.TextField(label="نهاية (HH:MM)")
        info = ft.Text()
        qr_image = ft.Image(width=240, height=240)

        def create_lecture(_e):
            try:
                course_id = int(course_dd.value)
                lec_id = m.create_lecture(course_id, date.value, start.value, end.value, qr_token=None)
                token = f"LECTURE|{lec_id}|NEW"
                with get_conn() as conn:
                    conn.execute("UPDATE lectures SET qr_token=? WHERE id=?", (token, lec_id)); conn.commit()
                path = generate_qr_png(token, f"lecture_{lec_id}.png")
                qr_image.src = path
                info.value = f"تم إنشاء المحاضرة #{lec_id} وتوليد QR."
                refresh_table(); page.update()
            except Exception as ex:
                info.value = f"خطأ: {ex}"; page.update()

        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("مقررID")),
            ft.DataColumn(ft.Text("تاريخ")), ft.DataColumn(ft.Text("وقت")),
            ft.DataColumn(ft.Text("Token")), ft.DataColumn(ft.Text("إجراءات"))
        ], rows=[])

        def refresh_table():
            table.rows = []
            for r in m.list_lectures():
                def edit_handler(rr=r):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل محاضرة #{rr['id']}"))
                        _date = ft.TextField(label="تاريخ", value=rr['lecture_date'])
                        _start = ft.TextField(label="بداية", value=rr['start_time'])
                        _end = ft.TextField(label="نهاية", value=rr['end_time'])
                        def save(__e):
                            if hasattr(m, "update_lecture"):
                                m.update_lecture(rr['id'], lecture_date=_date.value, start_time=_start.value, end_time=_end.value)
                            d.open=False; refresh_table(); page.update()
                        d.content = ft.Column([_date, _start, _end], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open=True; page.update()
                    return _
                def delete_handler(rr=r):
                    def _(_e):
                        if hasattr(m, "delete_lecture"):
                            m.delete_lecture(rr['id']); refresh_table(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r['id']))), ft.DataCell(ft.Text(str(r['course_id']))),
                    ft.DataCell(ft.Text(r['lecture_date'])),
                    ft.DataCell(ft.Text(f"{r['start_time']} - {r['end_time']}")),
                    ft.DataCell(ft.Text((r['qr_token'] or "")[:20] + ("..." if r['qr_token'] and len(r['qr_token'])>20 else ""))),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
        refresh_table()

        return ft.Column([
            ft.Text("إنشاء محاضرة وتوليد QR", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([course_dd, date, start, end, ft.ElevatedButton("إنشاء + QR", on_click=create_lecture)], spacing=8),
            info, ft.Row([qr_image]), ft.Text("جميع المحاضرات:"), table
        ], spacing=10)

    # ---- العلامات ----
    def grades_section():
        students = m.list_students()
        courses = m.list_courses()
        st_dd = ft.Dropdown(label="طالب", options=[ft.dropdown.Option(str(s['id']), f"{s['id']} - {s['full_name'] or s['username']}") for s in students])
        c_dd = ft.Dropdown(label="مقرر", options=[ft.dropdown.Option(str(c['id']), f"{c['code']} - {c['name']}") for c in courses])
        exam_type = ft.TextField(label="نوع", value="Final")
        grade = ft.TextField(label="علامة", value="80")
        info = ft.Text()

        def add_grade(_e):
            try:
                m.add_grade(int(st_dd.value), int(c_dd.value), exam_type.value, float(grade.value))
                info.value = "تم الحفظ."; refresh_table(); page.update()
            except Exception as ex:
                info.value = f"خطأ: {ex}"; page.update()

        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("طالبID")), ft.DataColumn(ft.Text("الاسم")),
            ft.DataColumn(ft.Text("رمز")), ft.DataColumn(ft.Text("مقرر")),
            ft.DataColumn(ft.Text("نوع")), ft.DataColumn(ft.Text("علامة")), ft.DataColumn(ft.Text("إجراءات"))
        ], rows=[])

        def refresh_table():
            table.rows = []
            for r in m.list_grades_all():
                def edit_handler(rr=r):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل علامة #{rr['id']}"))
                        _type = ft.TextField(label="نوع", value=rr['exam_type'])
                        _grade = ft.TextField(label="علامة", value=str(rr['grade']))
                        def save(__e):
                            if hasattr(m, "update_grade"):
                                m.update_grade(rr['id'], exam_type=_type.value, grade=float(_grade.value))
                            d.open = False; refresh_table(); page.update()
                        d.content = ft.Column([_type, _grade], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open = True; page.update()
                    return _
                def delete_handler(rr=r):
                    def _(_e):
                        if hasattr(m, "delete_grade"):
                            m.delete_grade(rr['id']); refresh_table(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r['id']))),
                    ft.DataCell(ft.Text(str(r['student_id']))),
                    ft.DataCell(ft.Text(r.get('full_name') or "")),
                    ft.DataCell(ft.Text(r['code'])),
                    ft.DataCell(ft.Text(r['name'])),
                    ft.DataCell(ft.Text(r['exam_type'])),
                    ft.DataCell(ft.Text(str(r['grade']))),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
        refresh_table()

        return ft.Column([
            ft.Text("إدارة العلامات", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([st_dd, c_dd, exam_type, grade, ft.ElevatedButton("إضافة", on_click=add_grade)], spacing=8),
            info, table
        ], spacing=10)

    # ---- المالية ----
    def finance_section():
        students = m.list_students()
        st_dd = ft.Dropdown(label="طالب", options=[ft.dropdown.Option(str(s['id']), f"{s['id']} - {s['full_name'] or s['username']}") for s in students])
        desc = ft.TextField(label="الوصف", value="قسط فصل")
        amount = ft.TextField(label="المبلغ", value="250")
        due = ft.TextField(label="الاستحقاق (YYYY-MM-DD)", value="")
        paid = ft.Checkbox(label="مدفوع؟")
        info = ft.Text()

        def add_due(_e):
            try:
                m.add_finance(int(st_dd.value), desc.value, float(amount.value), due.value or None, 1 if paid.value else 0)
                info.value = "تمت الإضافة."; refresh_table(); page.update()
            except Exception as ex:
                info.value = f"خطأ: {ex}"; page.update()

        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("طالبID")), ft.DataColumn(ft.Text("الوصف")),
            ft.DataColumn(ft.Text("المبلغ")), ft.DataColumn(ft.Text("الاستحقاق")),
            ft.DataColumn(ft.Text("مدفوع؟")), ft.DataColumn(ft.Text("إجراءات"))
        ], rows=[])

        def refresh_table():
            table.rows = []
            for r in m.list_finance_all():
                def edit_handler(rr=r):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل ذمة #{rr['id']}"))
                        _desc = ft.TextField(label="الوصف", value=rr['description'])
                        _amount = ft.TextField(label="المبلغ", value=str(rr['amount']))
                        _due = ft.TextField(label="الاستحقاق", value=rr['due_date'] or "")
                        _paid = ft.Checkbox(label="مدفوع؟", value=bool(rr['paid']))
                        def save(__e):
                            if hasattr(m, "update_finance"):
                                m.update_finance(rr['id'], description=_desc.value, amount=float(_amount.value),
                                                 due_date=_due.value or None, paid=1 if _paid.value else 0)
                            d.open=False; refresh_table(); page.update()
                        d.content = ft.Column([_desc, _amount, _due, _paid], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open=True; page.update()
                    return _
                def delete_handler(rr=r):
                    def _(_e):
                        if hasattr(m, "delete_finance"):
                            m.delete_finance(rr['id']); refresh_table(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r['id']))), ft.DataCell(ft.Text(str(r['student_id']))),
                    ft.DataCell(ft.Text(r['description'])), ft.DataCell(ft.Text(str(r['amount']))),
                    ft.DataCell(ft.Text(r['due_date'] or "-")),
                    ft.DataCell(ft.Text("نعم" if r['paid'] else "لا")),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
        refresh_table()

        return ft.Column([
            ft.Text("إدارة الذمم المالية", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([st_dd, desc, amount, due, paid, ft.ElevatedButton("إضافة", on_click=add_due)], spacing=8),
            info, table
        ], spacing=10)

    # ---- مواد الكليات (رفع ملفات) ----
    def materials_section():
        colleges = ["الهندسة", "الطب", "الصيدلة", "الحقوق"]
        dd = ft.Dropdown(label="الكلية", value=colleges[0],
                         options=[ft.dropdown.Option(c) for c in colleges])
        title = ft.TextField(label="عنوان المحاضرة")
        info = ft.Text()
        picker = ft.FilePicker()
        page.overlay.append(picker)

        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("الكلية")),
            ft.DataColumn(ft.Text("العنوان")),
            ft.DataColumn(ft.Text("الملف")),
            ft.DataColumn(ft.Text("تاريخ الرفع")),
            ft.DataColumn(ft.Text("إجراءات")),
        ], rows=[])

        def refresh():
            table.rows = []
            for r in m.list_materials(dd.value):
                def edit_handler(row=r):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text(f"تعديل #{row['id']}"))
                        _title = ft.TextField(label="العنوان", value=row["title"])
                        def save(__e):
                            m.update_material(row["id"], title=_title.value)
                            d.open = False; refresh(); page.update()
                        d.content = ft.Column([_title], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d, "open", False))]
                        page.dialog = d; d.open = True; page.update()
                    return _
                def delete_handler(row=r):
                    def _(_e):
                        m.delete_material(row["id"], delete_file=True)
                        refresh(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r["id"]))),
                    ft.DataCell(ft.Text(r["college"])),
                    ft.DataCell(ft.Text(r["title"])),
                    ft.DataCell(ft.Text(os.path.basename(r["file_path"]))),
                    ft.DataCell(ft.Text(r.get("uploaded_at") or "")),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ICONS.EDIT, tooltip="تعديل", on_click=edit_handler()),
                        ft.IconButton(icon=ICONS.DELETE, tooltip="حذف", on_click=delete_handler()),
                    ])),
                ]))
            page.update()

        def do_pick(_e):
            if not title.value:
                info.value = "أدخل عنوانًا أولًا."; page.update(); return
            picker.pick_files(allow_multiple=False)

        def on_pick(e: ft.FilePickerResultEvent):
            if not e.files:
                info.value = "لم يتم اختيار ملف."; page.update(); return
            f = e.files[0]
            try:
                m.add_material(dd.value, title.value.strip() or os.path.splitext(f.name)[0], f.path)
                info.value = "تم رفع الملف بنجاح."
                title.value = ""
                refresh()
            except Exception as ex:
                info.value = f"خطأ: {ex}"
            page.update()

        picker.on_result = on_pick
        refresh()

        return ft.Column([
            ft.Text("رفع محاضرات الكليات", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([dd, title, ft.ElevatedButton("اختيار ملف ورفع", on_click=do_pick)], spacing=8),
            info,
            table
        ], spacing=10)

    # ---- الباصات ----
    def buses_section():
        route = ft.TextField(label="الخط", value="Route A")
        depart = ft.TextField(label="الانطلاق (HH:MM)", value="07:30")
        origin = ft.TextField(label="من", value="باب المعظم")
        dest = ft.TextField(label="إلى", value="جامعة الرشيد")
        info = ft.Text()

        def add_bus(_e):
            try:
                m.add_bus(route.value, depart.value, origin.value, dest.value)
                info.value = "تم حفظ الموعد."
                refresh_table(); page.update()
            except Exception as ex:
                info.value = f"خطأ: {ex}"; page.update()

        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("الخط")), ft.DataColumn(ft.Text("الانطلاق")),
            ft.DataColumn(ft.Text("من")), ft.DataColumn(ft.Text("إلى")), ft.DataColumn(ft.Text("إجراءات"))
        ], rows=[])

        def refresh_table():
            table.rows = []
            for b in m.list_buses():
                def edit_handler(bb=b):
                    def _(_e):
                        d = ft.AlertDialog(modal=True, title=ft.Text("تعديل موعد باص"))
                        _route = ft.TextField(label="الخط", value=bb['route'])
                        _depart = ft.TextField(label="الانطلاق", value=bb['depart_time'])
                        _origin = ft.TextField(label="من", value=bb['origin'])
                        _dest = ft.TextField(label="إلى", value=bb['destination'])
                        def save(__e):
                            if hasattr(m, "update_bus"):
                                m.update_bus(bb['id'], route=_route.value, depart_time=_depart.value,
                                             origin=_origin.value, destination=_dest.value)
                            d.open=False; refresh_table(); page.update()
                        d.content = ft.Column([_route, _depart, _origin, _dest], tight=True)
                        d.actions = [ft.TextButton("حفظ", on_click=save),
                                     ft.TextButton("إغلاق", on_click=lambda e: setattr(d,'open',False))]
                        page.dialog = d; d.open=True; page.update()
                    return _
                def delete_handler(bb=b):
                    def _(_e):
                        if hasattr(m, "delete_bus"):
                            m.delete_bus(bb['id']); refresh_table(); page.update()
                    return _
                table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(b['route'])), ft.DataCell(ft.Text(b['depart_time'])),
                    ft.DataCell(ft.Text(b['origin'])), ft.DataCell(ft.Text(b['destination'])),
                    ft.DataCell(ft.Row([ft.IconButton(icon=ICONS.EDIT, on_click=edit_handler()),
                                        ft.IconButton(icon=ICONS.DELETE, on_click=delete_handler())]))
                ]))
        refresh_table()

        return ft.Column([
            ft.Text("مواعيد الباصات", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([route, depart, origin, dest, ft.ElevatedButton("إضافة", on_click=add_bus)], spacing=8),
            info, table
        ], spacing=10)

    sections = {
        0: ("الطلاب", students_section),
        1: ("المقررات", courses_section),
        2: ("المحاضرات & QR", lectures_section),
        3: ("العلامات", grades_section),
        4: ("المالية", finance_section),
        5: ("مواد الكليات", materials_section),
        6: ("الباصات", buses_section),
    }

    def set_section(i: int):
        title, builder = sections[i]
        content_container.content = ft.Container(builder(), padding=16)
        page.update()

    def do_logout(e=None):
        current_user["user"] = None
        page.views.clear()
        page.views.append(login_view(on_login, "جامعة الرشيد – الأدمن"))
        page.update()

    def appbar(title: str):
        logo = ft.Image(src=LOGO_PATH, height=32) if os.path.exists(LOGO_PATH) else None
        return ft.AppBar(title=ft.Text(title), bgcolor=APPBAR_BG, leading=logo,
                         actions=[ft.IconButton(icon=ICONS.LOGOUT, tooltip="تسجيل خروج", on_click=do_logout)])

    def show_home():
        rail = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(icon=ICONS.GROUP, label="الطلاب"),
                ft.NavigationRailDestination(icon=ICONS.BOOK, label="المقررات"),
                ft.NavigationRailDestination(icon=ICONS.QR_CODE, label="المحاضرات & QR"),
                ft.NavigationRailDestination(icon=ICONS.SCHOOL, label="العلامات"),
                ft.NavigationRailDestination(icon=ICONS.ACCOUNT_BALANCE_WALLET, label="المالية"),
                ft.NavigationRailDestination(icon=ICONS.ATTACH_FILE, label="مواد الكليات"),
                ft.NavigationRailDestination(icon=ICONS.DIRECTIONS_BUS, label="الباصات"),
            ],
            on_change=lambda e: set_section(e.control.selected_index)
        )
        page.views.clear()
        page.views.append(
            ft.View(route="/home", appbar=appbar("جامعة الرشيد – الأدمن"),
                    controls=[ft.Row([rail, ft.VerticalDivider(width=1),
                                      ft.Container(content_container, expand=True)], expand=True)], padding=0)
        )
        set_section(0); page.update()

    # ---- Login ----
    def on_login(username, password, info_text):
        user = verify_login(username, password)
        if not user:
            info_text.value = "بيانات الدخول غير صحيحة."; page.update(); return
        if user["role"] != "admin":
            info_text.value = "هذا التطبيق مخصص لمسؤولي الجامعة."; page.update(); return
        current_user["user"] = user
        show_home()

    page.views.append(login_view(on_login, "جامعة الرشيد – الأدمن"))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)