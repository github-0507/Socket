import socket
import os
import time
import threading
from tkinter import *
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import sys

# Thông tin
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432
IP_ADDRESS = 1 # Tạm

# Biến lưu trữ mã pin
client_pin = ""

# Hàm cập nhật thanh tiến trình
def update_progress_bar(progress_bar, label, value):
    progress_bar['value'] = value
    progress_bar.update_idletasks()
    label.config(text=f"{value:.0f}%")

def upload_file(client_socket, filepath, parent_window):
    try:
        if not os.path.exists(filepath):
            messagebox.showerror("Lỗi", f"Path {filepath} not found",parent = parent_window)
            return

        filename = os.path.basename(filepath)
        if os.path.isfile(filepath): # Up file
            client_socket.send(f"upload {filename}".encode('utf-8'))

            # Nhận thông báo từ server: tiếc tục gửi data
            client_socket.recv(1024)
            # Tính toán kích thước file
            total_size = os.path.getsize(filepath)
            byte_sent = 0
            # Thiết lập cửa sổ tiến trình
            progress_window = tk.Toplevel(parent_window)
            progress_window.title("Uploading File")
            progress_label = tk.Label(progress_window, text = f"Uploading {filename}...")
            progress_label.pack(pady=10)

            progress_bar = ttk.Progressbar(progress_window, length = 400, maximum = 100, mode = 'determinate')
            progress_bar.pack(pady=10)

            percent_label = tk.Label(progress_window, text = "0%", font = ("Helvetica", 10))
            percent_label.pack()

            # Upload
            with open(filepath, 'rb') as f:
                while (data := f.read(1024)):
                    try:
                        client_socket.send(data)
                        client_socket.recv(1024)
                        # Cập nhật byte đã gửi
                        byte_sent += len(data)
                        # Tính toán phần trăm và hiển thị tiến độ
                        progress = (byte_sent/total_size)*100
                        # Cập nhật tiến trình liên tục với phần trăm vừa tính
                        update_progress_bar(progress_bar, percent_label, progress)
                        progress_window.update()
                    except Exception as e:
                        messagebox.showerror("Lỗi", "Error handling server. Disconnected from server!")
                        sys.exit()
                        return
                        

            # Gửi thông báo END và thanh tiến trình dừng lại 1 giây
            client_socket.send(b'END')
            time.sleep(1)
            progress_window.destroy()

            # parent là biến: hiện thông báo lên từ cửa sổ nào
            messagebox.showinfo("Thông báo", client_socket.recv(1024).decode('utf-8'), parent = parent_window)
            
        elif os.path.isdir(filepath): # Up folder
            client_socket.send(f"folder_upload {filename}".encode('utf-8'))
            ack = client_socket.recv(1024)

            # os.walk duyệt qua từng thư mục và tệp con
            # trả về root: đường dẫn tuyệt đối thư mục đang xét
            # dirs: danh sách thư mục trong root
            # files: danh sách file trong root
            for root, dirs, files in os.walk(filepath):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, filepath)

                    # Gửi thông tin từng file
                    client_socket.send(f"file {relative_path}".encode('utf-8'))
                    ack = client_socket.recv(1024)
                    # Tính toán kích thước file
                    total_size = os.path.getsize(file_path)
                    byte_sent = 0
                    # Thiết lập cửa số thanh tiến trình
                    progress_window = tk.Toplevel(parent_window)
                    progress_window.title("Uploading File")
                    progress_label = tk.Label(progress_window, text = f"Uploading {file}...")
                    progress_label.pack(pady=10)

                    progress_bar = ttk.Progressbar(progress_window, length = 400, maximum = 100, mode = 'determinate')
                    progress_bar.pack(pady=10)

                    percent_label = tk.Label(progress_window, text = "0%", font = ("Helvetica", 10))
                    percent_label.pack()

                    # Gửi nội dung từng file
                    with open(file_path, 'rb') as f:
                        while (data := f.read(1024)):
                            try:
                                client_socket.send(data)
                                ack = client_socket.recv(1024)
                                # Cập nhật byte đã gửi
                                byte_sent += len(data)
                                # Tính toán phần trăm và hiển thị tiến độ
                                progress = (byte_sent/total_size)*100
                                # Cập nhật thanh tiến trình
                                update_progress_bar(progress_bar, percent_label, progress)
                                progress_window.update()
                            except Exception as e:
                                messagebox.showerror("Lỗi", "Error handling server. Disconnected from server!")
                                sys.exit()
                                return

                    client_socket.send(b'END')
                    ack = client_socket.recv(1024)

                    time.sleep(0.5)
                    progress_window.destroy()

            client_socket.send(b'FOLDER_END')
            client_socket.recv(1024)
            messagebox.showinfo("Thông báo!",client_socket.recv(1024).decode('utf-8'),parent = parent_window)
    except Exception as e:
        messagebox.showerror("Lỗi", "Error handling server. Disconnected from server!")
        sys.exit() # Thoát khỏi root và đi đến finally của hàm main

def download_file(client_socket, filename, download_path, parent_window):
    try:
        client_socket.send(f"download {filename}".encode())

        response = client_socket.recv(1024).decode()
        client_socket.send(b"ACK")

        if response.startswith("READY"):
            # Lấy kích thước file do bên server gửi về 
            _, file_size = response.split(" ")
            file_size = int(file_size)
            # Nếu đường dẫn lưu chưa có và hợp lệ thì tạo
            if not os.path.isdir(download_path):
                os.makedirs(download_path)
            # Tạo đường dẫn, nếu có thì chạy vòng lặp tạo tên cho đúng
            if(os.path.isfile(filename)):
                filename = os.path.basename(filename)
                file_path = os.path.join(download_path, filename)
                if os.path.isfile(file_path):
                    basename, extension = os.path.splitext(filename)
                    counter = 1
                    while os.path.isfile(file_path):
                        filename = f"{basename}({counter}){extension}"
                        file_path = os.path.join(download_path, filename)
                        counter += 1
            # Tạo đường dẫn, nếu có thì chạy vòng lặp tạo tên cho đúng
            elif(os.path.isdir(filename)):
                filename = f"{filename}.zip"
                filename = os.path.basename(filename)
                file_path = os.path.join(download_path, filename)
                if os.path.isfile(file_path):
                    basename, extension = os.path.splitext(filename)
                    counter = 1
                    while os.path.isfile(file_path):
                        filename = f"{basename}({counter}){extension}"
                        file_path = os.path.join(download_path, filename)
                        counter += 1
            byte_received = 0
            progress_window = tk.Toplevel(parent_window)
            progress_window.title("Downloading File")
            progress_label = tk.Label(progress_window, text=f"Downloading {filename}...")
            progress_label.pack(pady = 10)

            progress_bar = ttk.Progressbar(progress_window, length = 400, maximum = 100, mode = 'determinate')
            progress_bar.pack(pady = 10)

            percent_label = tk.Label(progress_window, text = "0%", font = ("Helvetica", 10))
            percent_label.pack()
            with open(file_path, 'wb') as f:
                while True:
                    try:
                        data = client_socket.recv(1024)
                        if data == b"END":
                            break
                        else:
                            f.write(data)
                            # Gửi thông báo đến server: tiếp tục gửi data
                            client_socket.send(b"ACK")
                            byte_received += len(data)
                            progress = (byte_received / file_size) * 100
                            # Cập nhật thanh tiến trình
                            update_progress_bar(progress_bar, percent_label, progress)
                            progress_window.update()
                    except Exception as e:
                        messagebox.showerror("Lỗi", "Error handling server. Disconnected from server!")
                        sys.exit()
                        return
            time.sleep(0.5)
            progress_window.destroy()

            def is_zip_file(filepath):
            # Kiểm tra phần mở rộng của file
                return os.path.splitext(filepath)[1].lower() == '.zip'
            if is_zip_file(file_path):
                messagebox.showinfo("Thông báo",f"Folder {filename} downloaded successfully",parent = parent_window)
            else:
                messagebox.showinfo("Thông báo",f"File {filename} downloaded successfully",parent = parent_window)
        else:
            messagebox.showinfo("Thông báo", response, parent = parent_window)
    except Exception as e:
        messagebox.showerror("Lỗi", "Error handling server. Disconnected from server!")
        sys.exit() # Thoát khỏi root và đi đến finally của hàm main

# Hàm chọn đường dẫn cho nút Browse
def browse_upload(upload):
    # Mở hộp thoại chọn tệp
    file_path = filedialog.askopenfilename(title="Chọn tệp để upload", filetypes=[("All files", "*.*")])  # Chọn tệp bất kỳ
    
    if file_path:  # Nếu có chọn tệp
        upload.delete(0, END)  # Xóa nội dung cũ
        upload.insert(0, file_path)  # Điền đường dẫn của tệp vào ô nhập

def browse_upload_folder(upload):
    # Mở hộp thoại chọn thư mục
    folder_path = filedialog.askdirectory(title = "Chọn thư mục để upload")  # Chọn thư mục
    
    if folder_path:
        upload.delete(0, END)
        upload.insert(0, folder_path)

def browse_download(download):
    file_path = filedialog.askopenfilename(title = "Chọn tệp để download", filetypes = [("All files", "*.*")])
    if file_path:
        download.delete(0, END)
        download.insert(0, file_path)

def browse_download_folder(download):
    folder_path = filedialog.askdirectory(title = "Chọn thư mục để download")
    if folder_path:
        download.delete(0, END)
        download.insert(0, folder_path)

def browse_download_path(download):
    folderpath = filedialog.askdirectory(title = "Chọn thư mục lưu file")
    if folderpath:
        download.delete(0, END)
        download.insert(0, folderpath)

# Nút Upload và ô text bên cạnh
def upload_action(client_socket, upload, parent):
    filepath = upload.get()
    upload_file(client_socket, filepath, parent)
    upload.delete(0, 'end')

# Nút Download và ô text bên cạnh
def download_action(client_socket, download_entry, download_path, parent):
    # Kiểm tra xem người dùng đã nhập đường dẫn tải về hay chưa
    if not download_path.get():
        messagebox.showerror("Lỗi", "Please select a download path")
        return
    
    file_path = download_path.get()
    while not os.path.isdir(file_path):
        messagebox.showerror("Lỗi", "Download path wrong")
        return
    
    if not download_entry.get():
        messagebox.showerror("Lỗi", "Please select a download file/folder")
        return

    filename = download_entry.get()  # Lấy dữ liệu từ ô Entry
    download_file(client_socket, filename, file_path, parent)

    download_entry.delete(0, 'end')
    download_path.delete(0, 'end')

# Cửa sổ Upload
def on_upload(root,client_socket):
    root.withdraw()  
    new_window = Toplevel(root)  # Tạo cửa sổ con mới
    new_window.title("Upload")  # Đặt tiêu đề cho cửa sổ con
    new_window.geometry("610x250")  # Kích thước cửa sổ con
    new_window.configure(bg='#B6C99B')
    Label(new_window, text = 'Upload', fg = 'white', bg = 'blue', font = ('Cambria', 16),
           width = 20).grid(row = 0, column = 0, columnspan = 3, pady = 20, sticky = 'n')

    # upload file
    upload_button = Button(new_window, text = "Upload file", font = ('Cambria', 12), fg = 'white', bg = 'blue',
                           command = lambda:upload_action(client_socket, upload_entry, new_window))
    upload_button.grid(row = 1, column = 0, padx = 10, pady = 10)

    upload_entry = Entry(new_window, width=40, font=('Cambria', 12))
    upload_entry.grid(row = 1, column = 1, padx = 10, pady = 10)

    upload_browse = Button(new_window, text = "Browse", font = ('Cambria', 10), fg = 'white', bg = 'blue', command = lambda:browse_upload(upload_entry))
    upload_browse.grid(row = 1, column = 2, padx = 10, pady = 10)

    # upload folder
    upload_button_folder = Button(new_window, text = "Upload folder", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
                                  command=lambda:upload_action(client_socket, upload_entry_folder, new_window))
    upload_button_folder.grid(row = 2, column = 0, padx = 10, pady = 10)

    upload_entry_folder = Entry(new_window, width=40, font=('Cambria', 12))
    upload_entry_folder.grid(row = 2, column = 1, padx = 10, pady = 10)

    upload_browse_folder = Button(new_window, text = "Browse", font = ('Cambria', 10), fg = 'white', bg = 'blue', 
                                  command=lambda:browse_upload_folder(upload_entry_folder))
    upload_browse_folder.grid(row = 2, column = 2, padx = 10, pady = 10)

    # Nút Close
    def on_close():
        root.deiconify()  # Hiển thị lại cửa sổ chính (root)
        new_window.destroy()  # Đóng cửa sổ con
    Button(new_window, text = "Close", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
        command = on_close).grid(row = 5, column = 0, columnspan = 3, pady = 20)

    # Cấu hình cột để căn giữa
    new_window.grid_columnconfigure(0, weight = 1)  # Cột trái
    new_window.grid_columnconfigure(1, weight = 1)  # Cột giữa
    new_window.grid_columnconfigure(2, weight = 1)  # Cột phải

    # Thực hiện on_close khi ấn dấu [x] tắt GUI
    new_window.protocol("WM_DELETE_WINDOW", on_close)

# Cửa sổ Download
def on_download(root, client_socket):
        root.withdraw()
        new_window = Toplevel(root)  # Tạo cửa sổ con mới
        new_window.title("Download")  # Đặt tiêu đề cho cửa sổ con
        new_window.geometry("610x280")  # Kích thước cửa sổ con
        new_window.configure(bg='#B6C99B')
        Label(new_window, text = "Download", fg = 'white', bg = 'blue', font = ('Cambria', 16), 
              width = 20).grid(row = 0, column = 0, columnspan = 3, pady = 20, sticky = 'n')
        
        # Đường dẫn lưu file sau khi tải về
        download_path_label = Label(new_window, text = "Download path:", font = ("Cambria", 12), fg = 'white', bg = 'blue')
        download_path_label.grid(row = 2, column = 0, padx = 10, pady = 5, sticky = W)

        download_path_entry = Entry(new_window, width = 40, font = ("Cambria", 12))
        download_path_entry.grid(row = 2, column = 1, padx = 5, pady = 5)

        download_path_browse = Button(new_window, text = "Browse", font = ('Cambria', 10), fg = 'white', bg = 'blue', 
                                      command = lambda:browse_download_path(download_path_entry))
        download_path_browse.grid(row = 2, column = 2, padx = 5, pady = 5)               
        
        # Nút download file
        download_button = Button(new_window, text = "Download file", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
                                 command = lambda:download_action(client_socket, download_entry, download_path_entry, new_window))
        download_button.grid(row = 3, column = 0, padx = 10, pady = 10)

        download_entry = Entry(new_window, width = 40, font = ('Cambria', 12))
        download_entry.grid(row = 3, column = 1, padx = 10, pady = 10)  

        download_browse = Button(new_window, text = "Browse", font = ('Cambria', 10), fg = 'white', bg = 'blue', 
                                 command = lambda:browse_download(download_entry))
        download_browse.grid(row = 3, column = 2, padx = 10, pady = 10)

        # Nút download folder
        download_button_folder = Button(new_window, text = "Download folder", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
                                        command = lambda:download_action(client_socket, download_entry_folder, download_path_entry, new_window))
        download_button_folder.grid(row = 4, column = 0, padx = 10, pady = 10)

        download_entry_folder = Entry(new_window, width=40, font = ('Cambria', 12))
        download_entry_folder.grid(row = 4, column = 1, padx = 10, pady = 10)

        download_browse_folder = Button(new_window, text = "Browse", font = ('Cambria', 10), fg = 'white', bg = 'blue', 
                                        command = lambda:browse_download_folder(download_entry_folder))
        download_browse_folder.grid(row = 4, column = 2, padx = 10, pady = 10)

        # Nút Close
        def on_close():
            root.deiconify()  # Hiển thị lại cửa sổ chính (root)
            new_window.destroy()  # Đóng cửa sổ con
        Button(new_window, text = "Close", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
               command = on_close).grid(row = 5, column = 0, columnspan = 3, pady = 20)

        # Cấu hình cột để căn giữa
        new_window.grid_columnconfigure(0, weight = 1)  # Cột trái
        new_window.grid_columnconfigure(1, weight = 1)  # Cột giữa
        new_window.grid_columnconfigure(2, weight = 1)  # Cột phải

        # Thực hiện on_close khi ấn dấu [x] tắt GUI
        new_window.protocol("WM_DELETE_WINDOW", on_close)

# Nút exit
def on_exit():
    result = messagebox.askquestion("Xác nhận thoát", "Disconnect from server?")
    if result == "yes":
        exit() # Đóng cửa sổ

# Check pin
def main_root(pin_root, client_socket):
    global client_pin

    if client_pin:
        # Gửi pin
        client_socket.send(f"{client_pin}".encode('utf-8'))

        pin = client_socket.recv(1024).decode('utf-8') # Check
        if pin != "READY":
            messagebox.showerror("Lỗi", "PIN wrong!")
            client_socket.close()

            time.sleep(1)
            pin_root.quit()  # Dừng vòng lặp và đóng cửa sổ chính
            return
    else:
        messagebox.showerror("Lỗi","Please enter the PIN")
        return

    # Ẩn cửa sổ chính
    pin_root.withdraw()

    # Tạo cửa sổ con mới
    root = Toplevel(pin_root)  # Tạo cửa sổ con từ pin_root
    root.title('TCP/IP')  # Đặt tiêu đề cho cửa sổ con
    root.geometry("500x250")  # Kích thước cửa sổ con
    root.configure(bg='#B6C99B')

    # Hiển thị thông tin
    Label(root, text = 'Socket', fg = 'red', font = ('Cambria', 16), width = 20).grid(row = 0, column = 0, columnspan = 3, pady = 20, sticky = 'n')
    Label(root, text = "Server Host:", font = ('Cambria', 12)).grid(row = 1, column = 0, sticky = 'w', padx = 10)
    Label(root, text = SERVER_HOST, font = ('Cambria', 12), fg = 'blue').grid(row = 1, column = 1, sticky = 'w', padx = 10)
    Label(root, text = "Server Port:", font = ('Cambria', 12)).grid(row = 2, column = 0, sticky = 'w', padx = 10)
    Label(root, text = SERVER_PORT, font = ('Cambria', 12), fg = 'blue').grid(row = 2, column = 1, sticky = 'w', padx = 10)
    Label(root, text = "Address Client:", font = ('Cambria', 12)).grid(row = 3, column = 0, sticky = 'w', padx = 10)
    Label(root, text = IP_ADDRESS, font = ('Cambria', 12), fg = 'blue').grid(row = 3, column = 1, sticky = 'w', padx = 10)

    # Nút upload
    upload_button = Button(root, text = "Upload", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
                           command=lambda: on_upload(root, client_socket))
    upload_button.grid(row = 5, column = 0, padx = 30, pady = 20, sticky = 'ew')

    # Nút download
    download_button = Button(root, text = "Download", font = ('Cambria', 12), fg = 'white', bg = 'blue', 
                             command=lambda: on_download(root, client_socket))
    download_button.grid(row = 5, column = 1, padx = 30, pady = 20, sticky = 'ew')

    # Nút exit
    exit_button = Button(root, text = "Exit", font = ('Cambria', 12), fg = 'white', bg = 'blue', command = on_exit)
    exit_button.grid(row = 5, column = 2, padx = 30, pady = 20, sticky = 'ew')

    # Đặt cấu hình lưới để các cột có kích thước đều
    root.grid_columnconfigure(0, weight = 1)
    root.grid_columnconfigure(1, weight = 1)
    root.grid_columnconfigure(2, weight = 1)

    def on_close(root, client_socket):
        client_socket.close()  # Đóng kết nối socket
        root.destroy()  # Đóng cửa sổ
        sys.exit() # Đóng chương trình

    # Thực hiện on_close khi ấn dấu [x] tắt GUI
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, client_socket))

# Hàm xử lý mã pin
def on_key_input(event, pin_entry):
    global client_pin
    char = event.char

    # Kiểm tra nếu phím Backspace, Delete
    if event.keysym in ("BackSpace", "Delete"):
        if len(client_pin) > 0:
            client_pin = client_pin[:-1]
            pin_entry.delete(0, END)
            pin_entry.insert(0, "*" * len(client_pin))
        return "break"  # Ngăn không cho ký tự gốc xuất hiện
    
    # Kiểm tra nếu phím nhấn không hợp lệ, isprintable: false nếu kí tự không thể in ra
    if not char.isprintable() or event.keysym in ("BackSpace", "Delete", "space"):
        return
    
    # Cập nhật nội dung thực tế
    client_pin += char
    pin_entry.delete(0, END)
    pin_entry.insert(0, "*" * len(client_pin))

    # Ngăn không cho ký tự gốc xuất hiện
    return "break"

def main(): # Tạo socket bằng phương thức TCP/IP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    IP_ADDRESS = client_socket.getsockname()[1]  # Lấy địa chỉ IP của client
    print("Connected to server")

    try: 
        # Tạo cửa sổ chính
        pin_root = Tk()
        pin_root.title('TCP/IP')
        pin_root.minsize(height = 250, width = 500)
        pin_root.configure(bg='black')  # Màu nền của cửa sổ chính là đen

        # Hiển thị tiêu đề "Pin"
        Label(pin_root, text = 'PIN', fg = 'white', bg = 'black', font = ('Cambria', 24), 
              width = 20).grid(row = 0, column = 0, columnspan = 3, pady = 20, sticky = 'n')

        pin_entry = Entry(pin_root, width = 40, font = ('Cambria', 12), bg = 'gray', fg = 'white')
        pin_entry.grid(row = 2, column = 1, padx = 10, pady = 10)

        # Ràng buộc sự kiện nhập liệu
        pin_entry.bind("<Key>", lambda event: on_key_input(event, pin_entry))

        # Nút Verify
        pin_button = Button(pin_root, text = "Verify", font = ('Cambria', 12), command = lambda: main_root(pin_root, client_socket), 
                            bg = 'green', fg = 'black', padx = 20, pady = 10)
        pin_button.grid(row = 3, column = 1, pady = 20, sticky = 'n')

        # Đặt cấu hình lưới để các cột có kích thước đều
        pin_root.grid_columnconfigure(0, weight = 1)
        pin_root.grid_columnconfigure(1, weight = 1)
        pin_root.grid_columnconfigure(2, weight = 1)

        pin_root.mainloop()  # Chạy vòng lặp chính của cửa sổ chính
        
    finally:
        client_socket.close()
        print("Disconnected from server")
        time.sleep(1)

if __name__ == "__main__":
    main()
