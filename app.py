"""
Complete Automatic JazzCash Donation Counter
Reads SMS from phone and updates counter live
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json
import os
import re
from threading import Thread
import time

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DATA_FILE = 'donations.json'
RATION_BAG_COST = 4500  # Rs. 4500 per bag

# ==================== DATA STORAGE ====================
def load_donations():
    """Load donations from file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_donations(donations):
    """Save donations to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(donations, f, indent=2)

# ==================== SMS PARSING ====================
def parse_jazzcash_sms(sms_text):
    """
    Parse JazzCash SMS to extract:
    - Amount
    - Sender name
    - Transaction ID
    """
    # Common JazzCash SMS patterns (adjust based on your actual SMS)
    patterns = [
        # Pattern 1: "Rs. 500 received from Muhammad Ali. Trx ID: JC123456"
        r'Rs\.?\s*(\d+[,\d]*)\s*(?:received|transferred|sent).*?(?:from|by)\s*([A-Za-z\s]+)\.?\s*(?:Trx|Transaction)?\s*(?:ID|id)?:?\s*([A-Z0-9]+)',
        
        # Pattern 2: "You received Rs.500 from Muhammad Ali (JC123456)"
        r'received\s*Rs\.?\s*(\d+[,\d]*)\s*from\s*([A-Za-z\s]+).*?([A-Z0-9]+)',
        
        # Pattern 3: "Transaction of Rs.500 from Muhammad Ali successful. ID: JC123456"
        r'Transaction.*?Rs\.?\s*(\d+[,\d]*).*?from\s*([A-Za-z\s]+).*?ID:?\s*([A-Z0-9]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            name = match.group(2).strip()
            transaction_id = match.group(3).strip()
            return {
                'amount': amount,
                'name': name,
                'transaction_id': transaction_id
            }
    
    return None

# ==================== API ENDPOINTS ====================
@app.route('/')
def index():
    """Main counter page"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Ramadan Rashan Drive 2026 - Live Counter</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #0a4d2e, #1a6b3c);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 15px;
        }
        
        .container {
            max-width: 1200px;
            width: 100%;
        }
        
        .main-card {
            background: white;
            border-radius: 40px;
            padding: 40px 30px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.3);
            text-align: center;
            border: 4px solid #d4af37;
        }
        
        .ramadan-title {
            font-size: 3rem;
            color: #0a4d2e;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        
        .ramadan-title span {
            font-size: 3.5rem;
        }
        
        .year {
            font-size: 2rem;
            color: #d4af37;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .total-section {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 30px;
            padding: 30px;
            margin: 30px 0;
        }
        
        .total-label {
            font-size: 1.5rem;
            color: #495057;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .total-amount {
            font-size: 6rem;
            font-weight: 800;
            color: #0a4d2e;
            line-height: 1.2;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .total-amount small {
            font-size: 2rem;
            color: #6c757d;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 40px 0;
        }
        
        .stat-box {
            background: #f8f9fa;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        }
        
        .stat-number {
            font-size: 3rem;
            font-weight: bold;
            color: #0a4d2e;
        }
        
        .stat-label {
            font-size: 1.2rem;
            color: #6c757d;
            margin-top: 10px;
        }
        
        .bags-section {
            background: linear-gradient(135deg, #d4af37, #ffd700);
            border-radius: 30px;
            padding: 30px;
            margin: 30px 0;
        }
        
        .bags-number {
            font-size: 5rem;
            font-weight: bold;
            color: #0a4d2e;
        }
        
        .bags-text {
            font-size: 2rem;
            color: #0a4d2e;
        }
        
        .recent-title {
            font-size: 2rem;
            color: #0a4d2e;
            margin: 40px 0 20px;
        }
        
        .donation-list {
            background: #f8f9fa;
            border-radius: 20px;
            padding: 20px;
        }
        
        .donation-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
            font-size: 1.2rem;
        }
        
        .donation-item:last-child {
            border-bottom: none;
        }
        
        .donor-name {
            font-weight: 600;
            color: #0a4d2e;
        }
        
        .donation-amount {
            font-weight: bold;
            color: #d4af37;
        }
        
        .donation-time {
            color: #6c757d;
        }
        
        .live-badge {
            display: inline-block;
            background: #dc3545;
            color: white;
            padding: 5px 15px;
            border-radius: 50px;
            font-size: 1rem;
            margin-bottom: 20px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .last-updated {
            color: #6c757d;
            margin-top: 30px;
            font-size: 1rem;
        }
        
        .loading {
            display: inline-block;
            width: 60px;
            height: 60px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #0a4d2e;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .hidden {
            display: none;
        }
        
        @media (max-width: 768px) {
            .ramadan-title { font-size: 2rem; }
            .total-amount { font-size: 4rem; }
            .stats-grid { grid-template-columns: 1fr; }
            .bags-number { font-size: 3.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-card">
            <div class="live-badge">🔴 LIVE</div>
            
            <div class="ramadan-title">
                <span>🌙</span> RAMADAN RASHAN DRIVE <span>🌙</span>
            </div>
            <div class="year">2026</div>
            
            <div id="loading" class="loading"></div>
            
            <div id="content" class="hidden">
                <div class="total-section">
                    <div class="total-label">TOTAL COLLECTED</div>
                    <div class="total-amount">
                        Rs. <span id="totalAmount">0</span><small>/=</small>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-number" id="totalDonations">0</div>
                        <div class="stat-label">Total Donations</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="avgDonation">0</div>
                        <div class="stat-label">Average Donation</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="todayDonations">0</div>
                        <div class="stat-label">Today's Donations</div>
                    </div>
                </div>
                
                <div class="bags-section">
                    <div class="bags-number" id="totalBags">0</div>
                    <div class="bags-text">Families Will Be Fed</div>
                    <div style="color:#0a4d2e; margin-top:10px;">Each Bag: Rs. 4,500</div>
                </div>
                
                <div class="recent-title">✨ Recent Donations</div>
                <div class="donation-list" id="recentDonations"></div>
            </div>
            
            <div class="last-updated">
                Last updated: <span id="lastUpdated">just now</span>
            </div>
        </div>
    </div>

    <script>
        function fetchStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDisplay(data);
                        document.getElementById('loading').classList.add('hidden');
                        document.getElementById('content').classList.remove('hidden');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }
        
        function updateDisplay(data) {
            const formatter = new Intl.NumberFormat('en-PK');
            
            document.getElementById('totalAmount').textContent = formatter.format(data.total_amount);
            document.getElementById('totalDonations').textContent = data.total_donations;
            document.getElementById('avgDonation').textContent = formatter.format(Math.round(data.avg_donation));
            document.getElementById('todayDonations').textContent = data.today_count;
            document.getElementById('totalBags').textContent = data.total_bags;
            
            const recentList = document.getElementById('recentDonations');
            recentList.innerHTML = '';
            
            data.recent_donations.forEach(donation => {
                const item = document.createElement('div');
                item.className = 'donation-item';
                item.innerHTML = `
                    <span class="donor-name">${donation.name}</span>
                    <span class="donation-amount">Rs. ${formatter.format(donation.amount)}</span>
                    <span class="donation-time">${donation.time}</span>
                `;
                recentList.appendChild(item);
            });
            
            const now = new Date();
            document.getElementById('lastUpdated').textContent = 
                now.toLocaleTimeString('en-PK', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                });
        }
        
        // Fetch every 5 seconds for real-time updates
        fetchStats();
        setInterval(fetchStats, 5000);
    </script>
</body>
</html>
    ''')

@app.route('/api/stats')
def get_stats():
    """Get current donation statistics"""
    donations = load_donations()
    
    if not donations:
        return jsonify({
            'success': True,
            'total_amount': 0,
            'total_donations': 0,
            'total_bags': 0,
            'avg_donation': 0,
            'today_count': 0,
            'recent_donations': []
        })
    
    total_amount = sum(d['amount'] for d in donations)
    total_donations = len(donations)
    total_bags = int(total_amount / RATION_BAG_COST)
    avg_donation = total_amount / total_donations if total_donations > 0 else 0
    
    # Today's donations
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = sum(1 for d in donations if d.get('date') == today)
    
    # Recent 10 donations
    recent = sorted(donations, key=lambda x: x['time'], reverse=True)[:10]
    recent_list = [{
        'name': d.get('name', 'Anonymous'),
        'amount': d['amount'],
        'time': d['time']
    } for d in recent]
    
    return jsonify({
        'success': True,
        'total_amount': total_amount,
        'total_donations': total_donations,
        'total_bags': total_bags,
        'avg_donation': round(avg_donation),
        'today_count': today_count,
        'recent_donations': recent_list
    })

# ==================== SMS WEBHOOK (From Your Phone) ====================
@app.route('/api/sms-webhook', methods=['POST'])
def sms_webhook():
    """Receive SMS from your phone"""
    try:
        data = request.json
        sms_text = data.get('sms', '')
        
        # Parse SMS
        parsed = parse_jazzcash_sms(sms_text)
        
        if parsed:
            donations = load_donations()
            
            # Check for duplicate
            for d in donations:
                if d['transaction_id'] == parsed['transaction_id']:
                    return jsonify({'status': 'duplicate'})
            
            # Add new donation
            now = datetime.now()
            donations.append({
                'transaction_id': parsed['transaction_id'],
                'amount': parsed['amount'],
                'name': parsed['name'],
                'time': now.strftime('%I:%M %p'),
                'date': now.strftime('%Y-%m-%d')
            })
            
            save_donations(donations)
            print(f"✅ Auto-recorded: Rs.{parsed['amount']} from {parsed['name']}")
            return jsonify({'status': 'success'})
        
        return jsonify({'status': 'ignored', 'reason': 'not a donation SMS'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'status': 'error'}), 500

# ==================== MANUAL ENTRY (For Testing) ====================
@app.route('/api/manual-add', methods=['POST'])
def manual_add():
    """Manually add a donation"""
    data = request.json
    donations = load_donations()
    
    now = datetime.now()
    donations.append({
        'transaction_id': f"MANUAL{len(donations)+1}",
        'amount': float(data['amount']),
        'name': data.get('name', 'Anonymous'),
        'time': now.strftime('%I:%M %p'),
        'date': now.strftime('%Y-%m-%d')
    })
    
    save_donations(donations)
    return jsonify({'success': True})

if __name__ == '__main__':
    # Create empty data file
    if not os.path.exists(DATA_FILE):
        save_donations([])
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
