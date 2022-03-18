#!/usr/bin/env python3

import os
import traceback
from tkinter import *
import requests
import webbrowser


auth_token_file = os.path.join(os.path.expanduser("~"), ".allosaurus_elan")


def center_window(root, width=300, height=200):
    # get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    # calculate position x and y coordinates
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    root.geometry('%dx%d+%d+%d' % (width, height, x, y))


def get_credentials():
    creds = []
    tk = Tk()
    tk.title('Log in')
    Label(tk, text='Username: ').grid(column=0, row=0, sticky=W)
    Label(tk, text='Password: ').grid(column=0, row=1, sticky=W)
    u = Entry(tk)
    u.grid(column=1, row=0, pady=2)
    u.focus_set()
    p = Entry(tk, show='*')
    p.grid(column=1, row=1, pady=2)
    u.bind('<Return>', lambda x:p.focus_set())
    b = Button(tk, text='Log in!', command=lambda:(lambda x:tk.destroy())(creds.extend([u.get(), p.get()])))
    b.grid(column=0, row=2, columnspan=2, pady=5)
    p.bind('<Return>', lambda x: b.invoke())
    tk.mainloop()
    return creds if creds else None

def ask_for_authtoken(server_url):
    authtoken = []
    tk = Tk()
    tk.title('Authorization required!')
    link1 = Label(tk, text="1. Click here to get your access token", fg="blue", cursor="hand2")
    link1.pack()
    link1.bind("<Button-1>", lambda e: browser_login(server_url))
    link2 = Label(tk, text="2. Paste your access token here:")
    link2.pack()
    u = Entry(tk)
    u.pack()
    u.focus_set()
    b = Button(tk, text='Save', command=lambda:(lambda x:tk.destroy())(authtoken.append(u.get().strip())))
    b.pack()
    u.bind('<Return>', lambda x: b.invoke())
    center_window(tk)
    tk.mainloop()
    with open(auth_token_file, 'w') as fout:
        fout.write(authtoken[0])
    return authtoken[0]

def browser_login(server_url):
    webbrowser.open(server_url + "/annotator/get_auth_token/")

def get_auth_token(server_url):
    creds = get_credentials()
    if not creds[0] or not creds[1]:
        return None
    url = server_url + "/api-token-auth/"
    try:
        r = requests.post(url, data={"username": creds[0], "password": creds[1]})
        with open(auth_token_file, 'w') as fout:
            fout.write(r.text.strip())
        return r.text.strip()
    except:
        sys.stderr.write("Error getting auth token from " + params['server_url'] + "\n")
        traceback.print_exc()
    return ""
