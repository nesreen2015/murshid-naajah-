# -*- coding: utf-8 -*-
"""
مرشد النجاة — Kivy + GPT + أوفلاين
"""

import os, sys, time, socket
import openai
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.metrics import dp

# مفتاح OpenAI
openai.api_key = "ضع_مفتاحك_هنا"

# تسجيل خط Cairo
FONT_NAME = None
if os.path.exists("Cairo-Regular.ttf"):
    LabelBase.register(name="CairoFont", fn_regular="Cairo-Regular.ttf")
    FONT_NAME = "CairoFont"
else:
    sys_font = "/system/fonts/NotoNaskhArabic-Regular.ttf"
    if os.path.exists(sys_font):
        LabelBase.register(name="SysArabic", fn_regular=sys_font)
        FONT_NAME = "SysArabic"
    else:
        FONT_NAME = None  # سيستخدم الخط الافتراضي

# إعداد حجم النافذة
Window.clearcolor = (0.68, 0.85, 0.96, 1)
Window.size = (390, 780)

# قاعدة بيانات الردود المحلية
SCENARIOS = {
    "خطر": "🚨 ابتعد فوراً عن المكان المهدد، واحتمِ في مكان آمن بعيداً عن النوافذ.",
    "قصف": "🛡️ انبطح قرب جدار داخلي، غطِّ رأسك، وانتظر حتى انقضاء الخطر.",
    "حريق": "🔥 اغادر المكان إن أمكن عبر طريق آمن، وإن لم تستطع فتجه إلى منطقة بعيدة عن الدخان.",
    "ماء": "💧 احفظ كمية مياه للشرب تدوم لعدة أيام، ولا تستهلكها إلا عند الحاجة.",
    "طعام": "🍞 خزّن طعامًا جافًا وسهل التحضير يكفي لعدة أيام.",
    "اسعاف": "⛑️ أوقف النزيف بالضغط المباشر، ونقل المصاب إن كان آمنًا، واطلب المساعدة الطبية."
}

# التحقق من الاتصال بالإنترنت
def is_connected(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except:
        return False

class GuideAvatar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = "calm"
        self.face_color = (0.53, 0.53, 0.53)
        self.eye_open = True
        self.hand_offset = 0
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_interval(self._blink, 3.0)
        Clock.schedule_interval(self._wave, 0.1)

    def _blink(self, dt):
        self.eye_open = False
        self.redraw()
        Clock.schedule_once(lambda dt: self._open_eye(), 0.12)

    def _open_eye(self):
        self.eye_open = True
        self.redraw()

    def _wave(self, dt):
        import math
        t = time.time()
        self.hand_offset = 6 * (1 + math.sin(t * 3))
        self.redraw()

    def set_state(self, state):
        self.state = state
        self.face_color = (1.0, 0.25, 0.25) if state == "alert" else (0.53, 0.53, 0.53)
        self.redraw()

    def redraw(self, *a):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        face_size = min(self.width, self.height) * 0.5
        face_x, face_y = cx - face_size / 2, cy - face_size / 2 + dp(6)
        with self.canvas:
            Color(*self.face_color)
            Ellipse(pos=(face_x, face_y), size=(face_size, face_size))
            eye_w = face_size * 0.12
            eye_h = eye_w if self.eye_open else eye_w * 0.18
            Color(0, 0, 0)
            Ellipse(pos=(face_x + face_size * 0.28, face_y + face_size * 0.58), size=(eye_w, eye_h))
            Ellipse(pos=(face_x + face_size * 0.6, face_y + face_size * 0.58), size=(eye_w, eye_h))
            Color(0, 0, 0)
            if self.state == "calm":
                Line(circle=(cx, face_y + face_size * 0.38, face_size * 0.16, 200, 340), width=dp(2))
            else:
                Line(points=[cx - face_size*0.12, face_y + face_size*0.28,
                             cx + face_size*0.12, face_y + face_size*0.28], width=dp(2))
            hand_w, hand_h = face_size * 0.36, face_size * 0.18
            Color(0.9, 0.9, 0.9)
            Ellipse(pos=(face_x - hand_w * 0.6, face_y + face_size*0.15 + self.hand_offset),
                    size=(hand_w, hand_h))
            Ellipse(pos=(face_x + face_size - hand_w * 0.1, face_y + face_size*0.15 - self.hand_offset),
                    size=(hand_w, hand_h))

class ChatScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=8, padding=10, **kwargs)
        self.avatar = GuideAvatar(size_hint_y=None, height=dp(160))
        self.add_widget(self.avatar)

        # الرسائل
        sv = ScrollView(size_hint=(1, 1))
        self.msg_container = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(4,4))
        self.msg_container.bind(minimum_height=self.msg_container.setter('height'))
        sv.add_widget(self.msg_container)
        self.add_widget(sv)

        # شريط الإدخال
        input_bar = BoxLayout(size_hint_y=None, height=dp(70), spacing=8)
        self.input = TextInput(hint_text="اكتب موقفك هنا...", font_name=FONT_NAME,
                               multiline=False, halign="right")
        send_btn = Button(text="إرسال", size_hint_x=None, width=dp(100),
                          background_color=(0.1,0.5,0.9,1), font_name=FONT_NAME)
        send_btn.bind(on_release=self.on_send)
        input_bar.add_widget(self.input)
        input_bar.add_widget(send_btn)
        self.add_widget(input_bar)

        Clock.schedule_once(lambda dt: self.add_bot_message(
            "🤝 مرحباً — أنا مرشدك للنجاة.\nتحدث معي بالعربية أو الإنجليزية."), 0.3)

    def add_user_message(self, text):
        lbl = Label(text=text, size_hint_y=None, halign="right", valign="middle",
                    text_size=(Window.width*0.68, None), font_name=FONT_NAME)
        lbl.color = (0,0,0,1)
        lbl.bind(texture_size=lambda inst, val: setattr(lbl, 'height', lbl.texture_size[1] + dp(12)))
        self.msg_container.add_widget(lbl)
        Clock.schedule_once(lambda dt: self.scroll_to_end(), 0.05)

    def add_bot_message(self, text):
        lbl = Label(text=text, size_hint_y=None, halign="right", valign="middle",
                    text_size=(Window.width*0.68, None), font_name=FONT_NAME)
        lbl.color = (0,0,0,1)
        lbl.bind(texture_size=lambda inst, val: setattr(lbl, 'height', lbl.texture_size[1] + dp(12)))
        self.msg_container.add_widget(lbl)
        Clock.schedule_once(lambda dt: self.scroll_to_end(), 0.05)

    def on_send(self, instance):
        text = (self.input.text or "").strip()
        if not text:
            return
        self.add_user_message(text)
        self.input.text = ""
        lowered = text.lower()
        for kw, advice in SCENARIOS.items():
            if kw in lowered:
                if kw in ["خطر", "قصف", "حريق"]:
                    self.avatar.set_state("alert")
                else:
                    self.avatar.set_state("calm")
                Clock.schedule_once(lambda dt, a=advice: self.add_bot_message(a), 0.25)
                return
        self.avatar.set_state("calm")
        Clock.schedule_once(lambda dt: self.get_reply(text), 0.25)

    def get_reply(self, prompt):
        if is_connected():
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "أنت مساعد ذكي للطوارئ."},
                              {"role": "user", "content": prompt}]
                )
                reply = resp.choices[0].message["content"].strip()
            except Exception as e:
                reply = f"⚠️ خطأ في الاتصال: {e}"
        else:
            reply = "📴 لا يوجد اتصال بالإنترنت، سأحاول مساعدتك من المعلومات المحلية."
        self.add_bot_message(reply)

    def scroll_to_end(self):
        try:
            self.children[1].scroll_y = 0
        except:
            pass

class MurshedApp(App):
    def build(self):
        self.title = "مرشد النجاة"
        return ChatScreen()

if __name__ == "__main__":
    MurshedApp().run()