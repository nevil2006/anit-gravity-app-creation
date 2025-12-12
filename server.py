import socket
import http.server
import socketserver
import json
import os
import datetime
import uuid

PORT = 8000
TASKS_FILE = 'tasks.json'
TODAY = datetime.date.today()

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def calculate_stats(tasks):
    total_weight = sum(t.get('weight', 1) for t in tasks)
    completed_weight = sum(t.get('weight', 1) for t in tasks if t.get('completed'))
    remaining_weight = total_weight - completed_weight
    progress = (completed_weight / total_weight * 100) if total_weight > 0 else 0
    return {
        "progress": progress,
        "completed_weight": completed_weight,
        "remaining_weight": remaining_weight,
        "total_weight": total_weight
    }

def get_dashboard_data(tasks):
    stats = calculate_stats(tasks)
    pie_data = [
        {"name": "Completed", "value": stats['completed_weight']},
        {"name": "Remaining", "value": stats['remaining_weight']}
    ]
    bar_data = []
    # Sort tasks: Today, Tomorrow, Week (simple sort by date)
    # We'll just return all for the frontend to sort or sort here.
    # Frontend can handle grouping, but let's send them sorted by due_date.
    sorted_tasks = sorted(tasks, key=lambda x: x.get('due_date', '9999-99-99'))
    
    for t in sorted_tasks:
        bar_data.append({
            "title": t.get('title', 'Untitled'),
            "completed_weight": t.get('weight', 1) if t.get('completed') else 0,
            "remaining_weight": t.get('weight', 1) if not t.get('completed') else 0
        })
        
    p = stats['progress']
    interp = f"Progress is at {p:.1f}%."
    if p >= 50:
        interp += " You are in good shape!"
    else:
        interp += " Focus on completing some tasks to reach the 50% milestone."
        
    return {
        "tasks": sorted_tasks,
        "progress": stats,
        "pie_data": pie_data,
        "bar_data": bar_data,
        "interpretation": interp
    }

class TaskHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/tasks':
            tasks = load_tasks()
            data = get_dashboard_data(tasks)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            req_json = json.loads(post_data) if post_data else {}
        except:
            req_json = {}

        tasks = load_tasks()
        
        if self.path == '/api/add':
            # { title, due_date, weight }
            current_ids = [t.get('id', 0) for t in tasks]
            new_id = (max(current_ids) + 1) if current_ids else 1
            
            # Default due date handling
            due = req_json.get('due_date', str(TODAY))
            if due == 'today': due = str(TODAY)
            elif due == 'tomorrow': due = str(TODAY + datetime.timedelta(days=1))
            
            new_t = {
                "id": new_id,
                "title": req_json.get('title', 'Untitled'),
                "due_date": due,
                "weight": int(req_json.get('weight', 1)),
                "completed": False
            }
            tasks.append(new_t)
            save_tasks(tasks)
            

        elif self.path == '/api/complete':
            # { id }
            t_id = int(req_json.get('id', -1))
            for t in tasks:
                if t.get('id') == t_id:
                    t['completed'] = not t['completed']
                    break
            save_tasks(tasks)

        elif self.path == '/api/delete':
            # { id }
            t_id = int(req_json.get('id', -1))
            tasks = [t for t in tasks if t.get('id') != t_id]
            save_tasks(tasks)

        elif self.path == '/api/edit':
            # { id, title, due_date, weight }
            t_id = int(req_json.get('id', -1))
            for t in tasks:
                if t.get('id') == t_id:
                    t['title'] = req_json.get('title', t['title'])
                    
                    due = req_json.get('due_date', t['due_date'])
                    if due == 'today': due = str(TODAY)
                    elif due == 'tomorrow': due = str(TODAY + datetime.timedelta(days=1))
                    t['due_date'] = due
                    
                    t['weight'] = int(req_json.get('weight', t['weight']))
                    break
            save_tasks(tasks)
            
        elif self.path == '/api/auto-50':
            # Logic: complete smallest weight non-protected tasks until progress >= 50%
            while True:
                stats = calculate_stats(tasks)
                if stats['progress'] >= 50:
                    break
                
                # Filter incomplete & non-protected
                candidates = [t for t in tasks if not t.get('completed') and 'protected' not in t.get('title', '').lower() and 'important' not in t.get('title', '').lower()]
                
                if not candidates:
                    break
                    
                # Sort by weight ascending
                candidates.sort(key=lambda x: x.get('weight', 1))
                
                # Complete smallest
                candidates[0]['completed'] = True
                
            save_tasks(tasks)

        # Return updated data
        data = get_dashboard_data(tasks)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    local_ip = get_ip()
    print(f"Server starting...")
    print(f"Local:   http://localhost:{PORT}")
    print(f"Network: http://{local_ip}:{PORT}")
    print("Press Ctrl+C to stop.")
    
    with socketserver.TCPServer(("", PORT), TaskHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
