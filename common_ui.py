\
import flet as ft

def login_view(on_login, app_title: str):
    username = ft.TextField(label="اسم المستخدم", autofocus=True)
    password = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True)
    info = ft.Text(color="red")

    def do_login(e):
        on_login(username.value.strip(), password.value.strip(), info)

    return ft.View(
        route="/",
        controls=[
            ft.AppBar(title=ft.Text(app_title), center_title=True),
            ft.Container(
                ft.Column([
                    ft.Text("تسجيل الدخول", size=24, weight=ft.FontWeight.BOLD),
                    username,
                    password,
                    ft.ElevatedButton("دخول", on_click=do_login),
                    info,
                ], tight=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                padding=20,
                expand=True,
                alignment=ft.alignment.center,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
