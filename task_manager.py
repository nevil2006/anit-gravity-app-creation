import json
import uuid
import datetime
import sys
import argparse

TASKS_FILE = 'tasks.json'
TODAY = datetime.date.today()

def load_tasks():
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def parse_date(date_str):
    if not date_str:
        return str(TODAY)
    date_str = date_str.lower()
    if date_str == 'today':
        return str(TODAY)
    elif date_str == 'tomorrow':
        return str(TODAY + datetime.timedelta(days=1))
    elif 'week' in date_str:
        # Assume 'this-week' means coming Sunday or just a marker. 
        # For sorting, let's put it at 7 days out or proper day.
        # Let's just return the string 'this-week' for display? 
        # But sorting needs a date. Let's default 'this-week' to +7 days for sorting purposes
        # but keep the original string if possible? The prompt asks to sort.
        return str(TODAY + datetime.timedelta(days=7)) 
    else:
        # Try YYYY-MM-DD
        try:
            return str(datetime.datetime.strptime(date_str, "%Y-%m-%d").date())
        except ValueError:
            return str(TODAY) # Fallback

def get_weight(w_str):
    try:
        w = int(w_str)
        return max(1, min(3, w))
    except (ValueError, TypeError):
        return 1

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

def add_task(args):
    tasks = load_tasks()
    # command format: ADD | TITLE | due:X | weight:Y
    # parts passed as args.parts
    # Reconstruct whole string first
    full_cmd = " ".join(args.parts)
    segments = [s.strip() for s in full_cmd.split('|')]
    
    # segments[0] is ADD (already handled)
    title = segments[1] if len(segments) > 1 else "Untitled"
    due_str = None
    weight_str = None
    
    for seg in segments[2:]:
        if seg.lower().startswith('due:'):
            due_str = seg.split(':', 1)[1].strip()
        elif seg.lower().startswith('weight:'):
            weight_str = seg.split(':', 1)[1].strip()
            
    current_ids = [t['id'] for t in tasks]
    new_id = 1
    if current_ids:
        new_id = max(current_ids) + 1
        
    new_task = {
        "id": new_id,
        "title": title,
        "due_date": parse_date(due_str),
        "weight": get_weight(weight_str),
        "completed": False
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return tasks

def complete_task(args):
    tasks = load_tasks()
    full_cmd = " ".join(args.parts)
    # COMPLETE | ID or TITLE
    segments = [s.strip() for s in full_cmd.split('|')]
    target = segments[1] if len(segments) > 1 else ""
    
    found = False
    # Try ID first
    try:
        t_id = int(target)
        for t in tasks:
            if t['id'] == t_id:
                t['completed'] = not t['completed'] # Toggle
                found = True
                break
    except ValueError:
        pass
    
    if not found:
        # Try title
        for t in tasks:
            if t['title'].lower() == target.lower():
                t['completed'] = not t['completed']
                found = True
                break
                
    save_tasks(tasks)
    return tasks

def auto_50(args):
    tasks = load_tasks()
    # Sort incomplete tasks by weight (asc)
    # Filter out important/protected? The prompt says "Do NOT touch tasks labeled important or protected."
    # We'll check title for keywords or just assume if not mentioned? 
    # Assumption: User will label them in title e.g. "Important Task"
    
    while True:
        stats = calculate_stats(tasks)
        if stats['progress'] >= 50:
            break
            
        incomplete = [t for t in tasks if not t['completed']]
        # Filter protected
        candidates = []
        for t in incomplete:
            title_lower = t['title'].lower()
            if 'important' in title_lower or 'protected' in title_lower:
                continue
            candidates.append(t)
            
        if not candidates:
            break # No more tasks to complete to reach 50%
            
        # Sort by weight ascending
        candidates.sort(key=lambda x: x['weight'])
        
        # Complete the smallest
        candidates[0]['completed'] = True
        
    save_tasks(tasks)
    return tasks

def generate_output(tasks, stats_before=None):
    stats_current = calculate_stats(tasks)
    
    # pie_data
    pie_data = [
        {"name": "Completed", "value": stats_current['completed_weight']},
        {"name": "Remaining", "value": stats_current['remaining_weight']}
    ]
    
    # bar_data
    bar_data = []
    for t in tasks:
        bar_data.append({
            "title": t['title'],
            "completed_weight": t['weight'] if t['completed'] else 0,
            "remaining_weight": t['weight'] if not t['completed'] else 0
        })
        
    # Interpretation
    p = stats_current['progress']
    interp = f"Progress is at {p:.1f}%."
    if p >= 50:
        interp += " You are in good shape!"
    else:
        interp += " Focus on completing some tasks to reach the 50% milestone."
        
    output = {
        "tasks": tasks,
        "progress_before": stats_before if stats_before else stats_current,
        "progress_after": stats_current,
        "pie_data": pie_data,
        "bar_data": bar_data,
        "interpretation": interp
    }
    print(json.dumps(output, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?', default='STATUS')
    parser.add_argument('parts', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    
    cmd = args.command.upper()
    tasks_before = load_tasks()
    stats_before = calculate_stats(tasks_before)
    
    if cmd == 'ADD':
        tasks = add_task(args)
    elif cmd == 'COMPLETE':
        tasks = complete_task(args)
    elif cmd == 'AUTO-50':
        tasks = auto_50(args)
    else:
        tasks = tasks_before # Just status
        
    generate_output(tasks, stats_before)

if __name__ == "__main__":
    main()
