from apscheduler.schedulers.background import BackgroundScheduler
from src.models import User, Report, Project, BigDataLog, BmkgData, NewsData, WeatherData
import datetime

def aggregate_big_data():
    try:
        print(f"[{datetime.datetime.now()}] Aggregating Big Data...", flush=True)
        # Get stats from simpel_db
        total_users = User.objects.count()
        total_reports = Report.objects.count()
        total_projects = Project.objects.count()
        
        # Get stats from bigdata_db
        total_bmkg = BmkgData.objects.count()
        total_news = NewsData.objects.count()
        total_weather = WeatherData.objects.count()
        
        # Save to big_data_logs collection in simpel_db
        log = BigDataLog(
            total_users=total_users,
            total_reports=total_reports,
            total_projects=total_projects,
            total_bmkg=total_bmkg,
            total_news=total_news,
            total_weather=total_weather
        )
        log.save()
        print(f"[{datetime.datetime.now()}] Big Data aggregated successfully!", flush=True)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error aggregating Big Data: {e}", flush=True)

def init_scheduler():
    scheduler = BackgroundScheduler()
    # Run every hour
    scheduler.add_job(func=aggregate_big_data, trigger="interval", hours=1)
    # Also run once after 15 seconds to ensure we have some initial data to show
    scheduler.add_job(func=aggregate_big_data, trigger="date", run_date=datetime.datetime.now() + datetime.timedelta(seconds=15))
    scheduler.start()
    return scheduler
