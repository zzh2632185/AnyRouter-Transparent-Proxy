import os
import sys
import signal
import threading


def _restart_via_exec():
    """使用 os.execv 自重启（无 Supervisor 环境）"""
    print("[Restart] Restarting via os.execv...")
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception as e:
        print(f"[Restart] Failed to reload .env (override=True): {e}")
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _restart_via_signal():
    """发送 SIGTERM 信号优雅退出（由 Supervisor 重启）"""
    print("[Restart] Sending SIGTERM to self (PID: {})...".format(os.getpid()))
    sys.stdout.flush()
    sys.stderr.flush()
    os.kill(os.getpid(), signal.SIGTERM)


def schedule_restart(delay: float = 1.0, strategy: str = "auto"):
    """
    调度服务重启

    Args:
        delay: 延迟时间（秒）
        strategy: 重启策略 ("auto", "signal", "exec")
            - "auto": 自动选择（默认 exec）
            - "signal": SIGTERM 信号（需要 Supervisor）
            - "exec": os.execv 自重启
    """
    if strategy == "auto":
        # 仅在明确存在 Supervisor 时使用 signal；默认 exec 以确保 .env 变更可生效
        has_supervisor = os.getenv("SUPERVISOR_ENABLED", "").lower() in ("true", "1", "yes")
        strategy = "signal" if has_supervisor else "exec"

    restart_func = _restart_via_signal if strategy == "signal" else _restart_via_exec

    print(f"[Restart] Scheduling restart in {delay}s using strategy: {strategy}")
    timer = threading.Timer(delay, restart_func)
    timer.daemon = True
    timer.start()
