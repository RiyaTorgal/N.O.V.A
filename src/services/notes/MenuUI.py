import tkinter as tk
from tkinter import messagebox
from src.dB.database import Database
from main.ui import ModernStickyNote

class NotesMenu:
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
        self.sticky_note = ModernStickyNote()  # For creating/editing notes

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

    def show_notes_menu(self):
        """Create a menu interface to view and manage notes."""
        popup = tk.Tk()
        popup.overrideredirect(True)
        popup.geometry("800x600+200+100")
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
        
        # N.O.V.A Notes Menu Title
        title_label = tk.Label(header_frame, 
                              text="N.O.V.A Notes Menu",
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
        
        # Notes List Frame
        notes_frame = tk.Frame(main_frame, bg=self.colors['card_bg'], padx=10, pady=10)
        notes_frame.pack(fill='both', expand=True)
        
        # Notes List Header
        tk.Label(notes_frame,
                text="Your Notes",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Canvas for scrollable notes list
        canvas = tk.Canvas(notes_frame, bg=self.colors['card_bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(notes_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['card_bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Fetch notes from database
        notes = self.db.get_all_notes()
        
        if not notes:
            tk.Label(scrollable_frame,
                    text="No notes found.",
                    bg=self.colors['card_bg'],
                    fg=self.colors['text_secondary'],
                    font=('Segoe UI', 10)).pack(anchor='w', pady=10)
        else:
            for note in notes:
                note_frame = tk.Frame(scrollable_frame, bg=self.colors['card_bg'], bd=1, relief='solid')
                note_frame.pack(fill='x', pady=5, padx=5)
                
                # Note Info
                tags = ", ".join([tag.name for tag in note.tags]) if note.tags else "None"
                info_text = f"{note.title} (ID: {note.id})\nTags: {tags}\nCreated: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                tk.Label(note_frame,
                        text=info_text,
                        bg=self.colors['card_bg'],
                        fg=self.colors['text'],
                        font=('Segoe UI', 10),
                        justify='left').pack(side='left', padx=10)
                
                # Action Buttons
                button_frame = tk.Frame(note_frame, bg=self.colors['card_bg'])
                button_frame.pack(side='right')
                
                # View Button
                def view_note(note=note):
                    view_popup = tk.Toplevel(popup)
                    view_popup.title(f"Note: {note.title}")
                    view_popup.geometry("600x400+300+200")
                    view_popup.configure(bg=self.colors['bg'])
                    
                    content_frame = tk.Frame(view_popup, bg=self.colors['card_bg'], padx=10, pady=10)
                    content_frame.pack(fill='both', expand=True)
                    
                    tk.Label(content_frame,
                            text=f"Title: {note.title}",
                            bg=self.colors['card_bg'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
                    
                    tk.Label(content_frame,
                            text=f"Tags: {tags}",
                            bg=self.colors['card_bg'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 10)).pack(anchor='w')
                    
                    tk.Label(content_frame,
                            text=f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                            bg=self.colors['card_bg'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 10)).pack(anchor='w')
                    
                    tk.Label(content_frame,
                            text=f"Priority: {note.priority or 'medium'}",
                            bg=self.colors['card_bg'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 10))
                    
                    text_area = tk.Text(content_frame,
                                       bg=self.colors['input_bg'],
                                       fg=self.colors['text'],
                                       font=('Segoe UI', 10),
                                       height=10,
                                       wrap=tk.WORD,
                                       state='normal')
                    text_area.insert("1.0", note.content)
                    text_area.configure(state='disabled')
                    text_area.pack(fill='both', expand=True, pady=(0, 10))
                
                view_btn = self.create_modern_button(button_frame, "View", view_note, '#3498db', '#2980b9')
                view_btn.pack(side='left', padx=5)
                
                # Edit Button
                def edit_note(note=note):
                    self.sticky_note.show_enhanced_sticky_note(note)
                
                edit_btn = self.create_modern_button(button_frame, "Edit", edit_note, '#f39c12', '#e67e22')
                edit_btn.pack(side='left', padx=5)
                
                # Delete Button
                def delete_note(note_id=note.id):
                    if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete note ID {note_id}?"):
                        if self.db.delete_note(note_id):
                            messagebox.showinfo("Success", "Note deleted successfully.")
                            popup.destroy()
                            self.show_notes_menu()  # Refresh the menu
                        else:
                            messagebox.showerror("Error", "Failed to delete note.")
                
                delete_btn = self.create_modern_button(button_frame, "Delete", delete_note, '#e74c3c', '#c0392b')
                delete_btn.pack(side='left', padx=5)
        
        # Action Buttons
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill='x', pady=(10, 0))
        
        create_btn = self.create_modern_button(button_frame, "Create New Note", lambda: self.sticky_note.show_enhanced_sticky_note(), '#27ae60', '#229954')
        create_btn.pack(anchor='center')
        
        popup.mainloop()

def show_notes_menu_popup():
    """Main function to show the notes menu."""
    notes_menu = NotesMenu()
    notes_menu.show_notes_menu()

if __name__ == "__main__":
    show_notes_menu_popup()