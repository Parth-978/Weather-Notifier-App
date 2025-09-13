import os
import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from plyer import notification


class WeatherNotifierApp:
    def __init__(self):
        # OpenWeatherMap API configuration
        self.API_KEY = "e91ea74d4f5b496b3e1286157a50d6e1"
        self.BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
        
        # Runtime state
        self.current_city = None
        self.notification_thread = None
        self.stop_notifications = False
        self.notifications_enabled = True
        self.current_theme = 'light'
        # Build UI and start background worker
        self.create_gui()
        self.start_notification_thread()

    def create_gui(self):
        """Builds the main window and all widgets."""
        self.root = tk.Tk()
        self.root.title("Weather Notifier App")
        self.root.geometry("560x460")
        self.root.resizable(False, False)

        # App icon (.ico preferred on Windows, PNG fallback)
        try:
            base_dir = os.path.dirname(__file__)
            ico_path = os.path.join(base_dir, "weather.ico")
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
            else:
                png_path = os.path.join(base_dir, "weather.png")
                if os.path.exists(png_path):
                    icon_img = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, icon_img)
        except Exception:
            pass

        self.center_window()

        # Set up ttk theme and styles
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.configure_styles(theme=self.current_theme)

        # Main container
        container = ttk.Frame(self.root, padding=(16, 16, 16, 12), style='App.TFrame')
        container.pack(fill='both', expand=True)

        # Header row
        header_row = ttk.Frame(container, style='App.TFrame')
        header_row.pack(fill='x')
        ttk.Label(header_row, text="🌤️ Weather Notifier", style='Header.TLabel').pack(side='left')

        controls_row = ttk.Frame(header_row, style='App.TFrame')
        controls_row.pack(side='right')
        self.dark_mode_var = tk.BooleanVar(value=(self.current_theme == 'dark'))
        ttk.Checkbutton(controls_row, text="Dark mode", variable=self.dark_mode_var,
                        command=lambda: self.switch_theme('dark' if self.dark_mode_var.get() else 'light'),
                        style='Switch.TCheckbutton').pack(side='right', padx=(8, 0))
        self.notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_row, text="Hourly notifications", variable=self.notify_var,
                        command=self.toggle_notifications, style='Switch.TCheckbutton').pack(side='right')
        ttk.Button(controls_row, text="Test API", command=self.test_api).pack(side='right', padx=(0, 8))

        # City input and action button
        input_card = ttk.Frame(container, padding=12, style='Card.TFrame')
        input_card.pack(fill='x', pady=(8, 0))
        input_inner = ttk.Frame(input_card, style='Card.TFrame')
        input_inner.pack(fill='x')
        ttk.Label(input_inner, text="Enter City Name", style='BodyStrong.TLabel').pack(side='left')
        self.city_entry = ttk.Entry(input_inner, width=28, font=('Arial', 12))
        self.city_entry.pack(side='left', padx=12)
        self.city_entry.bind('<Return>', lambda e: self.show_weather())
        self.fetch_button = ttk.Button(input_inner, text="Get Weather", style='Accent.TButton', command=self.show_weather)
        self.fetch_button.pack(side='left')

        self.progress = ttk.Progressbar(input_card, mode='indeterminate')
        self.progress.pack(fill='x', pady=(10, 0))
        self.progress.stop()

        # Weather details card
        self.weather_frame = ttk.Frame(container, padding=16, style='Card.TFrame')
        self.weather_frame.pack(pady=(8, 12), padx=0, fill='both', expand=True)
        self.city_label = ttk.Label(self.weather_frame, text="City: --", style='Title.TLabel')
        self.city_label.pack(pady=(0, 8))
        self.temp_label = ttk.Label(self.weather_frame, text="Temperature: --", style='Body.TLabel')
        self.temp_label.pack(pady=2)
        self.humidity_label = ttk.Label(self.weather_frame, text="Humidity: --", style='Body.TLabel')
        self.humidity_label.pack(pady=2)
        self.wind_label = ttk.Label(self.weather_frame, text="Wind Speed: --", style='Body.TLabel')
        self.wind_label.pack(pady=2)
        self.condition_label = ttk.Label(self.weather_frame, text="Condition: --", style='Body.TLabel')
        self.condition_label.pack(pady=2)

        # Status bar message
        self.status_label = ttk.Label(self.root, text="Enter a city to start hourly notifications", style='Status.TLabel', anchor='center')
        self.status_label.pack(fill='x', padx=12, pady=(0, 6))

        self.switch_theme(self.current_theme)

    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        pos_x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{pos_x}+{pos_y}')

    def get_weather(self, city):
        """Fetch weather data from OpenWeatherMap API."""
        if not self.API_KEY or self.API_KEY == "YOUR_API_KEY":
            raise Exception("Please set your OpenWeatherMap API key in the code.")
        params = {
            'q': city,
            'appid': self.API_KEY,
            'units': 'metric'
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                api_message = None
                try:
                    payload = response.json()
                    api_message = payload.get('message') or payload.get('cod')
                except Exception:
                    api_message = None
                if response.status_code == 404:
                    raise Exception(f"City '{city}' not found. Please check the spelling.")
                if response.status_code == 401:
                    raise Exception("Invalid API key or not activated yet. Verify your key.")
                if response.status_code == 429:
                    raise Exception("Rate limit exceeded (HTTP 429). Please wait and try again.")
                raise Exception(f"API Error: {response.status_code}{' - ' + str(api_message) if api_message else ''}")
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            raise Exception("No internet connection. Please check your network.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    def show_weather(self):
        """Fetch weather for the city in the entry and update the UI."""
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showwarning("Input Error", "Please enter a city name.")
            return

        self._set_loading(True)
        try:
            weather_data = self.get_weather(city)
            if weather_data:
                temp = weather_data['main']['temp']
                humidity = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']
                condition = weather_data['weather'][0]['description'].title()
                city_name = weather_data['name']
                country = weather_data['sys']['country']

                self.city_label.config(text=f"City: {city_name}, {country}")
                self.temp_label.config(text=f"Temperature: {temp}°C")
                self.humidity_label.config(text=f"Humidity: {humidity}%")
                self.wind_label.config(text=f"Wind Speed: {wind_speed} m/s")
                self.condition_label.config(text=f"Condition: {condition}")

                self.current_city = city
                if self.notifications_enabled:
                    self.set_status(f"Hourly notifications enabled for {city_name}", kind='success')
                else:
                    self.set_status(f"Notifications are disabled. Showing data for {city_name}", kind='info')

                if self.notifications_enabled:
                    self.send_notification()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self._set_loading(False)

    def _set_loading(self, is_loading: bool):
        self.root.update()
        try:
            if is_loading:
                self.progress.start(12)
            else:
                self.progress.stop()
        except Exception:
            pass

    def test_api(self):
        """Test API key with a known city and show result."""
        try:
            sample_city = 'London'
            data = self.get_weather(sample_city)
            if data:
                name = data.get('name', sample_city)
                temp = data.get('main', {}).get('temp')
                messagebox.showinfo("API Test Success", f"API key works. Sample city: {name}\nTemperature: {temp}°C")
                self.set_status("API test succeeded", kind='success')
            else:
                raise Exception("API key test failed")
        except Exception as e:
            messagebox.showerror("API Test Failed", str(e))
            self.set_status("API test failed", kind='error')
    
    def send_notification(self, weather_data=None):
        """Send desktop notification with weather information."""
        try:
            if weather_data is None and self.current_city:
                weather_data = self.get_weather(self.current_city)
            if weather_data:
                temp = weather_data['main']['temp']
                condition = weather_data['weather'][0]['description'].title()
                city_name = weather_data['name']
                notification.notify(
                    title=f"Weather Update - {city_name}",
                    message=f"Temperature: {temp}°C\nCondition: {condition}",
                    app_icon=None,
                    timeout=10,
                )
        except Exception as e:
            print(f"Notification error: {e}")

    def notification_worker(self):
        """Background loop to send hourly notifications."""
        while not self.stop_notifications:
            for _ in range(3600):
                if self.stop_notifications:
                    return
                time.sleep(1)
            if self.current_city and not self.stop_notifications:
                try:
                    self.send_notification()
                except Exception as e:
                    print(f"Hourly notification error: {e}")

    def start_notification_thread(self):
        if not self.notifications_enabled:
            return
        if self.notification_thread is None or not self.notification_thread.is_alive():
            self.stop_notifications = False
            self.notification_thread = threading.Thread(target=self.notification_worker, daemon=True)
            self.notification_thread.start()

    def stop_notification_thread(self):
        self.stop_notifications = True

    def toggle_notifications(self):
        self.notifications_enabled = bool(self.notify_var.get())
        if self.notifications_enabled:
            self.set_status("Hourly notifications enabled", kind='success')
            self.start_notification_thread()
        else:
            self.set_status("Hourly notifications disabled", kind='warning')
            self.stop_notification_thread()

    def set_status(self, text, kind='info'):
        style_map = {
            'info': 'Status.TLabel',
            'success': 'StatusSuccess.TLabel',
            'warning': 'StatusWarning.TLabel',
            'error': 'StatusError.TLabel',
        }
        self.status_label.configure(text=text, style=style_map.get(kind, 'Status.TLabel'))

    def configure_styles(self, theme='light'):
        """Define ttk styles for light and dark themes."""
        if theme == 'dark':
            bg = '#1f1f1f'
            card = '#2a2a2a'
            fg = '#e6e6e6'
            subfg = '#c0c0c0'
            accent = '#4FC3F7'
            success = '#66BB6A'
            warning = '#FFCA28'
            error = '#EF5350'
        else:
            bg = '#f6f7fb'
            card = '#ffffff'
            fg = '#222222'
            subfg = '#505050'
            accent = '#1976D2'
            success = '#2E7D32'
            warning = '#B26A00'
            error = '#C62828'

        self.style.configure('App.TFrame', background=bg)
        self.style.configure('Card.TFrame', background=card, borderwidth=1, relief='groove')
        self.style.configure('Header.TLabel', background=bg, foreground=fg, font=('Segoe UI', 18, 'bold'))
        self.style.configure('Title.TLabel', background=card, foreground=fg, font=('Segoe UI', 14, 'bold'))
        self.style.configure('BodyStrong.TLabel', background=card, foreground=fg, font=('Segoe UI', 11, 'bold'))
        self.style.configure('Body.TLabel', background=card, foreground=subfg, font=('Segoe UI', 11))
        self.style.configure('Status.TLabel', background=bg, foreground=subfg, font=('Segoe UI', 10))
        self.style.configure('StatusSuccess.TLabel', background=bg, foreground=success, font=('Segoe UI', 10, 'bold'))
        self.style.configure('StatusWarning.TLabel', background=bg, foreground=warning, font=('Segoe UI', 10, 'bold'))
        self.style.configure('StatusError.TLabel', background=bg, foreground=error, font=('Segoe UI', 10, 'bold'))
        self.style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'))
        self.style.map('Accent.TButton', foreground=[('disabled', subfg)], background=[('active', accent)])
        self.style.configure('TEntry', fieldbackground=card)
        self.style.configure('Switch.TCheckbutton', background=bg, foreground=subfg, font=('Segoe UI', 10))
        self.root.configure(bg=bg)

    def switch_theme(self, theme):
        if theme not in ('light', 'dark'):
            return
        self.current_theme = theme
        self.configure_styles(theme=theme)
        

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        self.stop_notification_thread()
        self.root.destroy()



try:
    app = WeatherNotifierApp()
    app.run()
except KeyboardInterrupt:
    print("\nApp interrupted by user")
except Exception as e:
    print(f"App error: {e}")
finally:
    print("Weather Notifier App closed")
