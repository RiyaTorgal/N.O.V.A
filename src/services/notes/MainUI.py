import tkinter as tk
from tkinter import messagebox, ttk
import datetime
from src.dB.database import Database
from src.dB.config import DB_CONFIG

class ModernStickyNote:
    def __init__(self):
        self.colors = {
            'bg': '#fff8dc',
            'card_bg': '#ffeb9c',
            'accent': '#f39c12',
            'success': '#f4a742',
            'warning': '#e67e22',
            'danger': '#e74c3c',
            'text': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'input_bg': '#fff2cc',
            'input_focus': '#ffe066'
        }
        self.db = Database()  # Initialize database connection

    def save_note(self, title, content, tags, priority='medium'):
        """Enhanced save function with metadata and database integration."""
        note_data = {
            'title': title,
            'content': content,
            'tags': tags,
            'priority': priority,
            'created_at': datetime.datetime.now().isoformat(),
            'word_count': len(content.split())
        }
        
        # Save to database
        note_id = self.db.save_note(title, content, tags, priority)
        if note_id:
            note_data['id'] = note_id
            print("=" * 50)
            print("N.O.V.A NOTE SAVED")
            print("=" * 50)
            print(f"Note ID: {note_id}")
            print(f"Title: {title}")
            print(f"Tags: {', '.join(tags) if tags else 'None'}")
            print(f"Priority: {priority.upper()}")
            print(f"Word Count: {note_data['word_count']}")
            print(f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)
            print(f"Content:\n{content}")
            print("=" * 50)
            return note_data
        else:
            print("Failed to save note to database.")
            return None

    def create_modern_entry(self, parent, placeholder="", height=1):
        """Create a modern styled entry widget."""
        if height == 1:
            entry = tk.Entry(parent, 
                            bg=self.colors['input_bg'],
                            fg=self.colors['text'],
                            insertbackground=self.colors['text'],
                            relief='flat',
                            font=('Segoe UI', 10),
                            bd=1,
                            highlightthickness=2,
                            highlightcolor=self.colors['accent'],
                            highlightbackground=self.colors['card_bg'])
        else:
            entry = tk.Text(parent,
                            bg=self.colors['input_bg'],
                            fg=self.colors['text'],
                            insertbackground=self.colors['text'],
                            relief='flat',
                            font=('Segoe UI', 10),
                            bd=1,
                            highlightthickness=2,
                            highlightcolor=self.colors['accent'],
                            highlightbackground=self.colors['card_bg'],
                            height=height,
                            wrap=tk.WORD)
        
        # Add placeholder functionality
        if placeholder and height == 1:
            entry.insert(0, placeholder)
            entry.configure(fg=self.colors['text_secondary'])
            
            def on_focus_in(event):
                if entry.get() == placeholder:
                    entry.delete(0, tk.END)
                    entry.configure(fg=self.colors['text'])
                    
            def on_focus_out(event):
                if not entry.get():
                    entry.insert(0, placeholder)
                    entry.configure(fg=self.colors['text_secondary'])
                    
            entry.bind('<FocusIn>', on_focus_in)
            entry.bind('<FocusOut>', on_focus_out)
            
        return entry

    def create_modern_button(self, parent, text, command, bg_color, hover_color=None):
        """Create a modern styled button."""
        if hover_color is None:
            hover_color = bg_color
            
        btn = tk.Button(parent,
                        text=text,
                        command=command,
                        bg=bg_color,
                        fg='white',
                        font=('Segoe UI', 11, 'bold'),
                        relief='raised',
                        bd=3,
                        padx=25,
                        pady=10,
                        cursor='hand2',
                        activebackground=hover_color,
                        activeforeground='white',
                        width=12,
                        height=1)
        
        # Add hover effects with shadow
        def on_enter(event):
            btn.configure(bg=hover_color, relief='raised', bd=4)
            
        def on_leave(event):
            btn.configure(bg=bg_color, relief='raised', bd=3)
            
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn

    def show_enhanced_sticky_note(self, note=None):
        """Create the enhanced sticky note interface for creating or editing a note."""
        popup = tk.Tk()
        popup.overrideredirect(True)
        popup.geometry("600x600+200+100")
        popup.configure(bg=self.colors['bg'])
        
        # Add subtle shadow effect
        shadow = tk.Frame(popup, bg='#f0e68c', height=2)
        shadow.pack(fill='x', side='bottom')
        
        # Main container
        main_frame = tk.Frame(popup, bg=self.colors['bg'], padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Header with drag functionality
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'], height=25)
        header_frame.pack(fill='x', pady=(0, 20))
        
        # N.O.V.A Logo/Title
        title_label = tk.Label(header_frame, 
                              text="N.O.V.A Notes",
                              bg=self.colors['bg'],
                              fg=self.colors['accent'],
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(side='left')
        
        # Close button
        close_btn = tk.Button(header_frame,
                             text="✕",
                             command=popup.destroy,
                             bg=self.colors['danger'],
                             fg='white',
                             font=('Segoe UI', 12, 'bold'),
                             relief='flat',
                             bd=0,
                             width=3,
                             height=1,
                             cursor='hand2')
        close_btn.pack(side='right')
        
        # Drag functionality
        def start_move(event):
            popup.x = event.x
            popup.y = event.y

        def stop_move(event):
            popup.x = None
            popup.y = None

        def do_move(event):
            deltax = event.x - popup.x
            deltay = event.y - popup.y
            x = popup.winfo_x() + deltax
            y = popup.winfo_y() + deltay
            popup.geometry(f"+{x}+{y}")

        header_frame.bind("<ButtonPress-1>", start_move)
        header_frame.bind("<ButtonRelease-1>", stop_move)
        header_frame.bind("<B1-Motion>", do_move)
        title_label.bind("<ButtonPress-1>", start_move)
        title_label.bind("<ButtonRelease-1>", stop_move)
        title_label.bind("<B1-Motion>", do_move)
        
        # Content Card
        content_frame = tk.Frame(main_frame, bg=self.colors['card_bg'], padx=10, pady=10)
        content_frame.pack(fill='both', expand=True)
        
        # Title Section
        tk.Label(content_frame, 
                text="Title",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        
        title_entry = self.create_modern_entry(content_frame, placeholder="Enter note title...")
        title_entry.pack(fill='x', pady=(0, 15))
        if note:
            title_entry.delete(0, tk.END)
            title_entry.insert(0, note.title)
            title_entry.configure(fg=self.colors['text'])
        
        # Tags and Priority Row
        tags_priority_frame = tk.Frame(content_frame, bg=self.colors['card_bg'])
        tags_priority_frame.pack(fill='x', pady=(0, 15))
        
        # Tags Section
        tags_frame = tk.Frame(tags_priority_frame, bg=self.colors['card_bg'])
        tags_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Label(tags_frame, 
                text="Tags",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        
        tags_entry = self.create_modern_entry(tags_frame, placeholder="work, ideas, important...")
        tags_entry.pack(fill='x', pady=(5, 0))
        if note and note.tags:
            tags_entry.delete(0, tk.END)
            tags_entry.insert(0, ", ".join([tag.name for tag in note.tags]))
            tags_entry.configure(fg=self.colors['text'])
        
        # Priority Section
        priority_frame = tk.Frame(tags_priority_frame, bg=self.colors['card_bg'])
        priority_frame.pack(side='right')
        
        tk.Label(priority_frame, 
                text="Priority",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        
        priority_var = tk.StringVar(value='medium')
        priority_combo = ttk.Combobox(priority_frame,
                                    textvariable=priority_var,
                                    values=['low', 'medium', 'high', 'urgent'],
                                    state='readonly',
                                    width=10,
                                    font=('Segoe UI', 10))
        priority_combo.configure(background='black')
        priority_combo.pack(pady=(5, 0))
        if note and note.priority:
            priority_var.set(note.priority)
        
        # Content Section
        tk.Label(content_frame, 
                text="Content",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        
        # Text area with scrollbar
        text_frame = tk.Frame(content_frame, bg=self.colors['card_bg'])
        text_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        content_text = self.create_modern_entry(text_frame, height=12)
        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=content_text.yview)
        content_text.configure(yscrollcommand=scrollbar.set)
        
        content_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        if note:
            content_text.delete("1.0", tk.END)
            content_text.insert("1.0", note.content)
        
        # Word count label
        word_count_label = tk.Label(content_frame,
                                    text="Words: 0",
                                    bg=self.colors['card_bg'],
                                    fg=self.colors['text_secondary'],
                                    font=('Segoe UI', 9))
        word_count_label.pack(anchor='e', pady=(0, 5))
        
        # Update word count
        def update_word_count(event=None):
            text = content_text.get("1.0", tk.END).strip()
            word_count = len(text.split()) if text else 0
            word_count_label.config(text=f"Words: {word_count}")
            
        content_text.bind('<KeyRelease>', update_word_count)
        update_word_count()  # Initial word count
        
        # Action Buttons
        button_frame = tk.Frame(content_frame, bg=self.colors['card_bg'])
        button_frame.pack(fill='x', pady=(5, 0))
        
        # Center the buttons
        button_container = tk.Frame(button_frame, bg=self.colors['card_bg'])
        button_container.pack(expand=True)
        
        # Save function
        def on_save():
            title = title_entry.get().strip()
            if title == "Enter note title...":
                title = ""
                
            tags_text = tags_entry.get().strip()
            if tags_text == "work, ideas, important...":
                tags_text = ""
                
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
            content = content_text.get("1.0", tk.END).strip()
            priority = priority_var.get()

            if not title or not content:
                messagebox.showwarning("Missing Fields", "Please enter both title and content.")
                return

            try:
                note_data = self.save_note(title, content, tags, priority)
                
                # Show success message
                success_popup = tk.Toplevel(popup)
                success_popup.overrideredirect(True)
                success_popup.geometry("300x100+300+250")
                success_popup.configure(bg=self.colors['success'])
                
                tk.Label(success_popup,
                        text="✓ Note Saved Successfully!",
                        bg=self.colors['success'],
                        fg='white',
                        font=('Segoe UI', 12, 'bold')).pack(expand=True)
                
                # Auto-close success popup
                success_popup.after(2000, success_popup.destroy)
                popup.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save note: {str(e)}")
        
        # Quick save function
        def on_quick_save():
            title = title_entry.get().strip()
            if not title or title == "Enter note title...":
                title = f"Quick Note {datetime.datetime.now().strftime('%H:%M')}"
                
            content = content_text.get("1.0", tk.END).strip()
            if not content:
                messagebox.showwarning("Missing Content", "Please enter some content.")
                return
                
            self.save_note(title, content, [], 'medium')
            popup.destroy()
        
        # Create buttons
        save_btn = self.create_modern_button(button_container, "Save Note", on_save, '#27ae60', '#229954')
        save_btn.pack(side='left', padx=8)
        
        quick_save_btn = self.create_modern_button(button_container, "Quick Save", on_quick_save, '#f39c12', '#e67e22')
        quick_save_btn.pack(side='left', padx=8)
        
        cancel_btn = self.create_modern_button(button_container, "Cancel", popup.destroy, '#95a5a6', '#7f8c8d')
        cancel_btn.pack(side='left', padx=8)
        
        # Keyboard shortcuts
        def on_key(event):
            if event.state & 0x4:  # Ctrl key
                if event.keysym == 's':
                    on_save()
                elif event.keysym == 'q':
                    on_quick_save()
                elif event.keysym == 'w':
                    popup.destroy()
        
        popup.bind('<KeyPress>', on_key)
        popup.focus_set()
        
        # Focus on title entry
        title_entry.focus()
        
        popup.mainloop()

def show_sticky_note_popup():
    """Main function to show the enhanced sticky note."""
    note_app = ModernStickyNote()
    note_app.show_enhanced_sticky_note()

if __name__ == "__main__":
    show_sticky_note_popup()