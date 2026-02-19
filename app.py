"""
JazzCash Donation Counter - Vercel Compatible Version
Uses cron jobs to check emails periodically
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json
import os
import re
import imaplib
import email
import hashlib

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DATA_FILE = '/tmp/donations.json'  # Vercel can write to /tmp
RATION_BAG_COST = 4500

# Email Configuration - CHANGE THESE!
EMAIL_ACCOUNT = "areezahmadch@gmail.com"
EMAIL_PASSWORD = "ecvc hdne jtfb cvup"  # Your App Password
FROM_EMAIL = "timeass59@gmail.com"  # Who sends the emails

# Secret key for cron job (CHANGE THIS!)
CRON_SECRET = "ramadan2026_secret_key_123"

# ==================== DATA STORAGE ====================
def load_donations():
    """Load donations from file"""
    # Try to load from /tmp first (writable in Vercel)
    if os.path.exists('/tmp/donations.json'):
        with open('/tmp/donations.json', 'r') as f:
            return json.load(f)
    # Fallback to local file (for development)
    elif os.path.exists('donations.json'):
        with open('donations.json', 'r') as f:
            return json.load(f)
    return []

def save_donations(donations):
    """Save donations to file"""
    # Save to /tmp for Vercel
    with open('/tmp/donations.json', 'w') as f:
        json.dump(donations, f, indent=2)
    # Also save locally for development
    with open('donations.json', 'w') as f:
        json.dump(donations, f, indent=2)

# ==================== SMS PARSING ====================
def parse_jazzcash_sms(sms_text):
    """
    Parse JazzCash SMS from email body
    Format: "Rs 10.00 received in your JazzCash Mobile Account:03095877041 via Raast. TID: 704100096110"
    """
    try:
        print(f"🔍 Parsing: {sms_text[:100]}...")
        
        # Extract amount
        amount_match = re.search(r'Rs\s*(\d+\.?\d*)', sms_text)
        if not amount_match:
            return None
        amount = float(amount_match.group(1))
        
        # Extract transaction ID
        tid_match = re.search(r'TID:\s*(\d+)', sms_text)
        transaction_id = tid_match.group(1) if tid_match else f"TXN{int(time.time())}"
        
        # Extract phone number
        phone_match = re.search(r'(\d{11})', sms_text)
        phone = phone_match.group(1) if phone_match else "Unknown"
        
        # Donor name
        name = "JazzCash Donor"
        
        return {
            'amount': amount,
            'name': name,
            'transaction_id': transaction_id,
            'phone': phone
        }
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None

# ==================== EMAIL CHECKER FUNCTION ====================
def check_emails_once():
    """
    Check emails once - called by cron endpoint
    Returns dict with results
    """
    print("📧 Checking emails once...")
    result = {
        'processed': 0,
        'found': 0,
        'errors': []
    }
    
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select('inbox')
        
        # Search for unread emails from your SMS Forwarder
        search_criteria = f'(UNSEEN FROM "{FROM_EMAIL}")'
        result_code, data = mail.search(None, search_criteria)
        
        email_ids = data[0].split()
        result['found'] = len(email_ids)
        
        print(f"📨 Found {len(email_ids)} new email(s)!")
        
        for email_id in email_ids:
            try:
                # Fetch the email
                result_code, data = mail.fetch(email_id, '(RFC822)')
                raw_email = data[0][1]
                
                # Parse email
                msg = email.message_from_bytes(raw_email)
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Parse SMS from email body
                donation = parse_jazzcash_sms(body)
                
                if donation:
                    print(f"💰 Parsed: Rs.{donation['amount']} - TID: {donation['transaction_id']}")
                    
                    # Load existing donations
                    donations = load_donations()
                    
                    # Check for duplicate
                    exists = False
                    for d in donations:
                        if d['transaction_id'] == donation['transaction_id']:
                            exists = True
                            print(f"⏭️ Duplicate transaction, skipping")
                            break
                    
                    if not exists:
                        # Add new donation
                        now = datetime.now()
                        donations.append({
                            'transaction_id': donation['transaction_id'],
                            'amount': donation['amount'],
                            'name': donation['name'],
                            'phone': donation.get('phone', ''),
                            'time': now.strftime('%I:%M %p'),
                            'date': now.strftime('%Y-%m-%d')
                        })
                        save_donations(donations)
                        result['processed'] += 1
                        print(f"✅✅✅ ADDED TO COUNTER: Rs.{donation['amount']}")
                        print(f"📊 Total donations now: {len(donations)}")
                else:
                    print("❌ Could not parse donation from email")
                
                # Mark as read
                mail.store(email_id, '+FLAGS', '\\Seen')
                print(f"✅ Email marked as read")
                
            except Exception as e:
                error_msg = f"Error processing email {email_id}: {str(e)}"
                print(f"❌ {error_msg}")
                result['errors'].append(error_msg)
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        error_msg = f"IMAP connection error: {str(e)}"
        print(f"❌ {error_msg}")
        result['errors'].append(error_msg)
    
    return result

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    """Main counter page"""
    return '''<!DOCTYPE html>
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
        
        .last-updated {
            color: #6c757d;
            margin-top: 30px;
            font-size: 1rem;
        }
        
        .status-badge {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 5px 15px;
            border-radius: 50px;
            font-size: 0.9rem;
            margin-top: 20px;
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
            
            <div id="content">
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
                    <div class="bags-text">Families Fed</div>
                    <div style="color:#0a4d2e; margin-top:10px;">Each Bag: Rs. 4,500</div>
                </div>
                
                <div class="recent-title">✨ Recent Donations</div>
                <div class="donation-list" id="recentDonations"></div>
            </div>
            
            <div class="last-updated">
                Last updated: <span id="lastUpdated">just now</span>
            </div>
            <div class="status-badge" id="autoUpdateStatus">Auto-updates every 30 seconds</div>
        </div>
    </div>

    <script>
        function fetchStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDisplay(data);
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateDisplay(data) {
            const formatter = new Intl.NumberFormat('en-PK');
            
            document.getElementById('totalAmount').textContent = formatter.format(data.total_amount);
            document.getElementById('totalDonations').textContent = data.total_donations;
            document.getElementById('avgDonation').textContent = formatter.format(data.avg_donation);
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
            
            document.getElementById('lastUpdated').textContent = 
                new Date().toLocaleTimeString();
        }
        
        // Fetch every 30 seconds
        fetchStats();
        setInterval(fetchStats, 30000);
    </script>
</body>
</html>
    '''

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

@app.route('/api/cron-check-emails')
def cron_check_emails():
    """Endpoint called by cron job service"""
    # Check secret for security
    secret = request.args.get('secret')
    if secret != CRON_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Run email check
    result = check_emails_once()
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'result': result
    })

@app.route('/api/manual-add', methods=['POST'])
def manual_add():
    """Manually add a donation for testing"""
    data = request.json
    donations = load_donations()
    
    now = datetime.now()
    donations.append({
        'transaction_id': f"MANUAL{len(donations)+1}",
        'amount': float(data['amount']),
        'name': data.get('name', 'Manual Entry'),
        'time': now.strftime('%I:%M %p'),
        'date': now.strftime('%Y-%m-%d')
    })
    
    save_donations(donations)
    return jsonify({'success': True})

@app.route('/api/status')
def status():
    """Check if the app is running"""
    donations = load_donations()
    return jsonify({
        'status': 'online',
        'total_donations': len(donations),
        'last_check': datetime.now().isoformat()
    })

# ==================== FOR LOCAL DEVELOPMENT ====================
if __name__ == '__main__':
    # Create empty data file if it doesn't exist
    if not os.path.exists('donations.json'):
        save_donations([])
        print("📁 Created empty donations file")
    
    print("\n" + "="*60)
    print("🚀 RAMADAN RASHAN DRIVE 2026 - LOCAL DEVELOPMENT")
    print("="*60)
    print("📧 Email account:", EMAIL_ACCOUNT)
    print("📧 Checking from:", FROM_EMAIL)
    print("="*60)
    print("\n✅ Server running at http://localhost:5002")
    print("⏰ For production: Use cron job service")
    print("="*60)
    
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
