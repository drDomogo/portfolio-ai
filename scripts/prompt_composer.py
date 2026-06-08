import os
import wx
import traceback
from openai import OpenAI
# Import nowego klienta Google Gemini
from google import genai
from google.genai import types


class MainFrame(wx.Frame):

    def __init__(self):
        super().__init__(
            None,
            title="AI Prompt Runner (OpenAI & Gemini)",
            size=(900, 700)
        )

        # Inicjalizacja klienta OpenAI (zachowana oryginalna konfiguracja)
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=300
        )

        # Inicjalizacja klienta Gemini (pobiera klucz z osobnej zmiennej środowiskowej)
        self.gemini_client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY")
        )

        self.attachment_paths = []

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        #
        # MODEL
        #
        model_box = wx.BoxSizer(wx.HORIZONTAL)
        model_box.Add(
            wx.StaticText(panel, label="Model:"),
            0,
            wx.ALL | wx.CENTER,
            5
        )

        # Zintegrowana lista modeli dla obu dostawców
        self.model_choice = wx.Choice(
            panel,
            choices=[
                "gpt-5",
                "gpt-5-mini",
                "gemini-2.5-pro",
                "gemini-2.5-flash"
            ]
        )
        self.model_choice.SetSelection(0)

        model_box.Add(
            self.model_choice,
            1,
            wx.ALL | wx.EXPAND,
            5
        )
        main_sizer.Add(model_box, 0, wx.EXPAND)

        #
        # SYSTEM PROMPT
        #
        main_sizer.Add(wx.StaticText(panel, label="System Prompt (.md)"), 0, wx.ALL, 5)
        self.system_path = wx.TextCtrl(panel)
        btn_system = wx.Button(panel, label="Wybierz")
        btn_system.Bind(wx.EVT_BUTTON, self.on_select_system)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.system_path, 1, wx.EXPAND | wx.ALL, 5)
        row.Add(btn_system, 0, wx.ALL, 5)
        main_sizer.Add(row, 0, wx.EXPAND)

        #
        # USER PROMPT
        #
        main_sizer.Add(wx.StaticText(panel, label="User Prompt (.md)"), 0, wx.ALL, 5)
        self.user_path = wx.TextCtrl(panel)
        btn_user = wx.Button(panel, label="Wybierz")
        btn_user.Bind(wx.EVT_BUTTON, self.on_select_user)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.user_path, 1, wx.EXPAND | wx.ALL, 5)
        row.Add(btn_user, 0, wx.ALL, 5)
        main_sizer.Add(row, 0, wx.EXPAND)

        #
        # ATTACHMENTS
        #
        main_sizer.Add(wx.StaticText(panel, label="Załączniki"), 0, wx.ALL, 5)
        btn_attach = wx.Button(panel, label="Dodaj pliki")
        btn_attach.Bind(wx.EVT_BUTTON, self.on_add_attachments)
        main_sizer.Add(btn_attach, 0, wx.ALL, 5)

        self.attachments_list = wx.ListBox(panel)
        main_sizer.Add(self.attachments_list, 1, wx.EXPAND | wx.ALL, 5)

        #
        # OUTPUT FILE
        #
        main_sizer.Add(wx.StaticText(panel, label="Plik wynikowy"), 0, wx.ALL, 5)
        self.output_path = wx.TextCtrl(panel)
        btn_output = wx.Button(panel, label="Wybierz")
        btn_output.Bind(wx.EVT_BUTTON, self.on_select_output)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.output_path, 1, wx.EXPAND | wx.ALL, 5)
        row.Add(btn_output, 0, wx.ALL, 5)
        main_sizer.Add(row, 0, wx.EXPAND)

        #
        # LOG
        #
        self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        main_sizer.Add(self.log, 1, wx.EXPAND | wx.ALL, 5)

        #
        # SEND
        #
        btn_send = wx.Button(panel, label="Wyślij zapytanie")
        btn_send.Bind(wx.EVT_BUTTON, self.on_send)
        main_sizer.Add(btn_send, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(main_sizer)
        self.Centre()

    def log_msg(self, msg):
        self.log.AppendText(msg + "\n")

    def on_select_system(self, event):
        with wx.FileDialog(self, "Wybierz system.md", wildcard="Markdown (*.md)|*.md", style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.system_path.SetValue(dlg.GetPath())

    def on_select_user(self, event):
        with wx.FileDialog(self, "Wybierz user.md", wildcard="Markdown (*.md)|*.md", style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.user_path.SetValue(dlg.GetPath())

    def on_add_attachments(self, event):
        with wx.FileDialog(self, "Dodaj pliki", style=wx.FD_OPEN | wx.FD_MULTIPLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                paths = dlg.GetPaths()
                for p in paths:
                    self.attachment_paths.append(p)
                    self.attachments_list.Append(p)

    def on_select_output(self, event):
        with wx.FileDialog(self, "Zapisz wynik", wildcard="Text (*.txt)|*.txt",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output_path.SetValue(dlg.GetPath())

    def read_text_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def on_send(self, event):
        import time
        from google.genai import errors

        try:
            system_file = self.system_path.GetValue()
            user_file = self.user_path.GetValue()
            output_file = self.output_path.GetValue()

            if not system_file: raise Exception("Brak system.md")
            if not user_file: raise Exception("Brak user.md")
            if not output_file: raise Exception("Brak pliku wynikowego")

            selected_model = self.model_choice.GetStringSelection()
            self.log_msg("Wczytywanie promptów...")

            system_prompt = self.read_text_file(system_file)
            user_prompt = self.read_text_file(user_file)

            # =================================================
            # ŚCIEŻKA DLA GOOGLE GEMINI
            # =================================================
            if "gemini" in selected_model:
                self.log_msg("Przetwarzanie załączników dla Gemini...")
                contents = []

                for path in self.attachment_paths:
                    file_content = self.read_text_file(path)
                    filename = os.path.basename(path)
                    contents.append(f"--- ZAŁĄCZNIK: {filename} ---\n{file_content}\n\n")
                    self.log_msg(f"Wczytano lokalnie: {filename}")

                contents.append(user_prompt)

                # Parametry pętli ponawiania prób
                max_retries = 3
                answer = None

                for attempt in range(max_retries):
                    try:
                        self.log_msg(
                            f"Wysyłanie zapytania do Google Gemini ({selected_model})... Próba {attempt + 1}/{max_retries}")
                        response = self.gemini_client.models.generate_content(
                            model=selected_model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                temperature=0.2,
                            ),
                        )
                        answer = response.text
                        break  # Sukces! Wychodzimy z pętli ponawiania


                    except (errors.ClientError, errors.ServerError) as e:

                        # Sprawdzamy czy to błąd limitu (429) lub przeciążenia serwera (503)

                        if e.code in [429, 503]:

                            if attempt < max_retries - 1:

                                wait_time = 10  # Czas oczekiwania w sekundach

                                if e.code == 503:

                                    self.log_msg(
                                        "Serwer Gemini jest przeciążony (503). Automatyczne oczekiwanie 10s...")

                                else:

                                    self.log_msg(
                                        "Przekroczono limit darmowych tokenów (429). Automatyczne oczekiwanie 10s...")

                                time.sleep(wait_time)

                                continue  # Przejdź do kolejnej próby w pętli

                        # Jeśli to inny błąd niż 429/503 lub ostatnia próba, wyrzuć błąd wyżej

                        raise e

                if not answer:
                    raise Exception("Nie udało się pobrać odpowiedzi z Gemini po kilku próbach.")

            # =================================================
            # ŚCIEŻKA DLA OPENAI (Oryginalna funkcjonalność)
            # =================================================
            else:
                self.log_msg("Upload załączników do OpenAI...")
                uploaded_files = []

                for path in self.attachment_paths:
                    uploaded = self.openai_client.files.create(
                        file=open(path, "rb"),
                        purpose="user_data"
                    )
                    uploaded_files.append(uploaded.id)
                    self.log_msg(f"Upload OK: {os.path.basename(path)}")

                content = [{"type": "input_text", "text": user_prompt}]

                for file_id in uploaded_files:
                    content.append({"type": "input_file", "file_id": file_id})

                self.log_msg(f"Wysyłanie zapytania do OpenAI ({selected_model})...")
                response = self.openai_client.responses.create(
                    model=selected_model,
                    instructions=system_prompt,
                    input=[{"role": "user", "content": content}]
                )
                answer = response.output_text

            # =================================================
            # ZAPIS WYNIKU (Wspólny dla obu modeli)
            # =================================================
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(answer)

            self.log_msg(f"Zapisano odpowiedź:\n{output_file}")
            wx.MessageBox("Gotowe", "Sukces", wx.OK | wx.ICON_INFORMATION)

        except Exception as ex:
            error_text = traceback.format_exc()
            print(error_text)
            self.log_msg(error_text)
            wx.MessageBox(error_text, "Błąd", wx.OK | wx.ICON_ERROR)


class App(wx.App):
    def OnInit(self):
        frame = MainFrame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = App(False)
    app.MainLoop()
