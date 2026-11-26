from flask import Flask, request, jsonify
import sqlite3



                    # id INTEGER PRIMARY KEY AUTOINCREMENT,
                    # name TEXT,
                    # father_name TEXT,
                    # mother_name TEXT,
                    # dob TEXT,
                    # roll_number TEXT UNIQUE,
                    # class TEXT,
                    # section TEXT,
                    # stream TEXT,
                     # optional_sub TEXT,
                    # language_lit TEXT




class Server:
    def __init__(self):
        pass

    def receive(self):
        data = request.get_json()

        if not data:
            return jsonify({
                "successs": False,
                "message": "Invalid JSON"
            }, 400)
        
        


