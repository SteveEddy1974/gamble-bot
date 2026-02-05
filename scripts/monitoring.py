#!/usr/bin/env python3
"""
Real-time monitoring dashboard and alerting system.

Features:
- Real-time balance and P&L tracking
- Prometheus metrics integration
- Alert triggers for critical events
- Performance dashboard
- Risk monitoring
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import logging
from datetime import datetime, timedelta
from collections import deque
import json
from typing import Dict, List, Any, Optional

# Alert thresholds
ALERT_BALANCE_DROP_PCT = 15  # Alert if balance drops 15%
ALERT_DRAWDOWN_PCT = 20  # Alert if drawdown exceeds 20%
ALERT_API_ERROR_COUNT = 5  # Alert after 5 consecutive API errors
ALERT_NO_BETS_MINUTES = 30  # Alert if no bets for 30 minutes


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, log_file: str = 'alerts.log'):
        self.log_file = log_file
        self.alerts_sent = deque(maxlen=100)
        self.alert_cooldowns = {}  # alert_type -> last_sent_time
        self.cooldown_seconds = 300  # 5 minutes between same alert type
        
        logging.basicConfig(
            filename=log_file,
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AlertManager')
    
    def send_alert(self, alert_type: str, message: str, severity: str = 'WARNING'):
        """Send an alert if not in cooldown period."""
        now = time.time()
        last_sent = self.alert_cooldowns.get(alert_type, 0)
        
        if now - last_sent < self.cooldown_seconds:
            return  # In cooldown
        
        self.alert_cooldowns[alert_type] = now
        
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity,
        }
        
        self.alerts_sent.append(alert)
        
        if severity == 'CRITICAL':
            self.logger.critical(f"[{alert_type}] {message}")
            print(f"\n🚨 CRITICAL ALERT: {message}")
        elif severity == 'WARNING':
            self.logger.warning(f"[{alert_type}] {message}")
            print(f"\n⚠️  WARNING: {message}")
        else:
            self.logger.info(f"[{alert_type}] {message}")
            print(f"\nℹ️  INFO: {message}")
    
    def get_recent_alerts(self, count: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return list(self.alerts_sent)[-count:]


class PerformanceMonitor:
    """Monitors bot performance and triggers alerts."""
    
    def __init__(self, starting_balance: float, alert_manager: AlertManager):
        self.starting_balance = starting_balance
        self.alert_manager = alert_manager
        
        # State tracking
        self.peak_balance = starting_balance
        self.last_bet_time = datetime.now()
        self.consecutive_api_errors = 0
        self.balance_history = deque(maxlen=1000)
        self.pnl_history = deque(maxlen=1000)
        
        # Performance metrics
        self.total_bets = 0
        self.winning_bets = 0
        self.losing_bets = 0
        self.total_pnl = 0.0
    
    def update(self, current_balance: float, api_error: bool = False):
        """Update monitoring state and check alert conditions."""
        now = datetime.now()
        
        # Track balance
        self.balance_history.append({
            'timestamp': now.isoformat(),
            'balance': current_balance,
        })
        
        # Check balance drop alert
        balance_drop_pct = ((self.peak_balance - current_balance) / self.peak_balance) * 100
        if balance_drop_pct >= ALERT_BALANCE_DROP_PCT:
            self.alert_manager.send_alert(
                'BALANCE_DROP',
                f"Balance dropped {balance_drop_pct:.1f}% from peak (£{self.peak_balance:.2f} → £{current_balance:.2f})",
                'WARNING'
            )
        
        # Update peak
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Check drawdown alert
        drawdown_pct = ((self.peak_balance - current_balance) / self.peak_balance) * 100
        if drawdown_pct >= ALERT_DRAWDOWN_PCT:
            self.alert_manager.send_alert(
                'DRAWDOWN',
                f"Drawdown at {drawdown_pct:.1f}% (peak: £{self.peak_balance:.2f}, current: £{current_balance:.2f})",
                'CRITICAL'
            )
        
        # Check API error alert
        if api_error:
            self.consecutive_api_errors += 1
            if self.consecutive_api_errors >= ALERT_API_ERROR_COUNT:
                self.alert_manager.send_alert(
                    'API_ERRORS',
                    f"{self.consecutive_api_errors} consecutive API errors - connection issues?",
                    'CRITICAL'
                )
        else:
            self.consecutive_api_errors = 0
        
        # Check no bets alert
        time_since_bet = (now - self.last_bet_time).total_seconds() / 60
        if time_since_bet >= ALERT_NO_BETS_MINUTES:
            self.alert_manager.send_alert(
                'NO_BETS',
                f"No bets placed for {time_since_bet:.0f} minutes - check market conditions",
                'WARNING'
            )
    
    def record_bet(self, profit: float):
        """Record a bet result."""
        self.last_bet_time = datetime.now()
        self.total_bets += 1
        
        if profit > 0:
            self.winning_bets += 1
        else:
            self.losing_bets += 1
        
        self.total_pnl += profit
        
        self.pnl_history.append({
            'timestamp': datetime.now().isoformat(),
            'profit': profit,
            'cumulative_pnl': self.total_pnl,
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        win_rate = (self.winning_bets / self.total_bets * 100) if self.total_bets > 0 else 0
        current_balance = self.balance_history[-1]['balance'] if self.balance_history else self.starting_balance
        roi = ((current_balance - self.starting_balance) / self.starting_balance) * 100
        drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100
        
        return {
            'current_balance': current_balance,
            'starting_balance': self.starting_balance,
            'peak_balance': self.peak_balance,
            'roi': roi,
            'drawdown': drawdown,
            'total_bets': self.total_bets,
            'winning_bets': self.winning_bets,
            'losing_bets': self.losing_bets,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'consecutive_api_errors': self.consecutive_api_errors,
            'last_bet_time': self.last_bet_time.isoformat(),
        }


class DashboardDisplay:
    """Real-time dashboard display."""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display(self, stats: Dict[str, Any], alerts: List[Dict]):
        """Display dashboard."""
        self.clear_screen()
        
        print("=" * 80)
        print("BACCARAT BOT - LIVE MONITORING DASHBOARD")
        print("=" * 80)
        
        # Runtime
        runtime = datetime.now() - self.start_time
        hours = int(runtime.total_seconds() // 3600)
        minutes = int((runtime.total_seconds() % 3600) // 60)
        print(f"\nRuntime: {hours}h {minutes}m | Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        
        # Balance metrics
        print("\n" + "─" * 80)
        print("BALANCE & P&L")
        print("─" * 80)
        print(f"  Current Balance:  £{stats['current_balance']:,.2f}")
        print(f"  Starting Balance: £{stats['starting_balance']:,.2f}")
        print(f"  Peak Balance:     £{stats['peak_balance']:,.2f}")
        print(f"  Total P&L:        £{stats['total_pnl']:+,.2f}")
        print(f"  ROI:              {stats['roi']:+.2f}%")
        
        # Risk metrics
        print("\n" + "─" * 80)
        print("RISK METRICS")
        print("─" * 80)
        
        drawdown_status = "🟢" if stats['drawdown'] < 10 else "🟡" if stats['drawdown'] < 20 else "🔴"
        print(f"  {drawdown_status} Current Drawdown: {stats['drawdown']:.2f}%")
        
        balance_vs_peak = ((stats['current_balance'] - stats['peak_balance']) / stats['peak_balance']) * 100
        balance_status = "🟢" if balance_vs_peak >= -5 else "🟡" if balance_vs_peak >= -15 else "🔴"
        print(f"  {balance_status} vs Peak:          {balance_vs_peak:+.2f}%")
        
        # Betting statistics
        print("\n" + "─" * 80)
        print("BETTING STATISTICS")
        print("─" * 80)
        print(f"  Total Bets:       {stats['total_bets']}")
        print(f"  Winning Bets:     {stats['winning_bets']} ({stats['win_rate']:.1f}%)")
        print(f"  Losing Bets:      {stats['losing_bets']}")
        
        if stats['total_bets'] > 0:
            avg_profit = stats['total_pnl'] / stats['total_bets']
            print(f"  Avg Profit/Bet:   £{avg_profit:+.2f}")
        
        # System health
        print("\n" + "─" * 80)
        print("SYSTEM HEALTH")
        print("─" * 80)
        
        api_status = "🟢 Healthy" if stats['consecutive_api_errors'] == 0 else f"🔴 {stats['consecutive_api_errors']} errors"
        print(f"  API Status:       {api_status}")
        
        last_bet_time = datetime.fromisoformat(stats['last_bet_time'])
        minutes_since_bet = (datetime.now() - last_bet_time).total_seconds() / 60
        bet_status = "🟢 Active" if minutes_since_bet < 5 else "🟡 Slow" if minutes_since_bet < 15 else "🔴 Stalled"
        print(f"  Betting Activity: {bet_status} (last bet {minutes_since_bet:.0f}m ago)")
        
        # Recent alerts
        if alerts:
            print("\n" + "─" * 80)
            print("RECENT ALERTS")
            print("─" * 80)
            for alert in alerts[-5:]:
                timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%H:%M:%S')
                severity_icon = "🚨" if alert['severity'] == 'CRITICAL' else "⚠️" if alert['severity'] == 'WARNING' else "ℹ️"
                print(f"  {severity_icon} [{timestamp}] {alert['message']}")
        
        print("\n" + "=" * 80)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 80)


def simulate_live_monitoring():
    """Simulate live monitoring for demonstration."""
    alert_manager = AlertManager()
    monitor = PerformanceMonitor(1000.0, alert_manager)
    dashboard = DashboardDisplay()
    
    # Simulate some activity
    balance = 1000.0
    
    try:
        for i in range(100):
            # Simulate betting activity
            if i % 5 == 0:
                # Place a bet
                import random
                won = random.random() > 0.45
                profit = random.uniform(5, 20) if won else -random.uniform(3, 15)
                balance += profit
                monitor.record_bet(profit)
            
            # Simulate occasional API errors
            api_error = (i % 23 == 0)
            
            # Update monitoring
            monitor.update(balance, api_error)
            
            # Display dashboard
            stats = monitor.get_stats()
            alerts = alert_manager.get_recent_alerts()
            dashboard.display(stats, alerts)
            
            time.sleep(2)  # Update every 2 seconds
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        print(f"\nFinal Statistics:")
        stats = monitor.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")


def main():
    print("=" * 80)
    print("MONITORING & ALERTING SYSTEM")
    print("=" * 80)
    print("\nThis script provides real-time monitoring and alerting.")
    print("\nFeatures:")
    print("  • Live balance and P&L tracking")
    print("  • Automatic alerts for critical events")
    print("  • Risk metrics monitoring")
    print("  • System health checks")
    print("\nAlert Thresholds:")
    print(f"  • Balance drop: {ALERT_BALANCE_DROP_PCT}%")
    print(f"  • Drawdown: {ALERT_DRAWDOWN_PCT}%")
    print(f"  • API errors: {ALERT_API_ERROR_COUNT} consecutive")
    print(f"  • No bets: {ALERT_NO_BETS_MINUTES} minutes")
    print("\n" + "=" * 80)
    
    response = input("\nRun demo? (y/n): ")
    if response.lower() == 'y':
        print("\nStarting live monitoring demo...")
        print("(This simulates bot activity for demonstration)")
        time.sleep(2)
        simulate_live_monitoring()
    else:
        print("\nTo integrate with your bot:")
        print("  1. Import: from monitoring import PerformanceMonitor, AlertManager")
        print("  2. Initialize: alert_mgr = AlertManager()")
        print("  3. Initialize: monitor = PerformanceMonitor(start_balance, alert_mgr)")
        print("  4. Update: monitor.update(current_balance, api_error=False)")
        print("  5. Record bets: monitor.record_bet(profit)")


if __name__ == '__main__':
    main()
