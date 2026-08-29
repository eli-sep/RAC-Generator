import tkinter as tk


def generate_names():
    prefix = prefix_entry.get()
    separator = separator_entry.get()
    start = int(start_entry.get())
    end = int(end_entry.get())

    output.delete("1.0", tk.END)

    for number in range(start, end + 1):
        equipment_name = f"{prefix}{separator}{number:02d}"
        output.insert(tk.END, equipment_name + "\n")


root = tk.Tk()
root.title("RAC Generator")

tk.Label(root, text="Equipment Name").pack()
prefix_entry = tk.Entry(root)
prefix_entry.pack()

tk.Label(root, text="Separator").pack()
separator_entry = tk.Entry(root)
separator_entry.pack()

tk.Label(root, text="Starting Number").pack()
start_entry = tk.Entry(root)
start_entry.pack()

tk.Label(root, text="Ending Number").pack()
end_entry = tk.Entry(root)
end_entry.pack()

generate_button = tk.Button(
    root,
    text="Generate",
    command=generate_names
)
generate_button.pack()

output = tk.Text(root, height=15, width=30)
output.pack()

root.mainloop()