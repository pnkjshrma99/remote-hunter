"""Business logic services."""

from app.services.analytics import (
    get_analytics_dashboard,
    get_job_market_heatmap,
    get_remote_hiring_trends,
    get_salary_insights,
    get_source_performance,
    update_source_performance_metrics,
)
from app.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    authenticate_user,
    create_email_verification,
    verify_email_code,
    verify_email_token,
    create_session,
    get_session_by_token,
    revoke_session,
    revoke_all_user_sessions,
    update_last_login,
    create_or_update_oauth_user,
)
from app.services.companies import (
    get_or_create_company,
    update_company_from_job,
    get_company_jobs,
    get_company_stats,
    list_all_companies,
    search_companies,
)
from app.services.job_bundles import (
    create_default_job_bundles,
    list_job_bundles,
    get_job_bundle,
    get_featured_job_bundles,
    increment_bundle_view,
    increment_bundle_purchase,
)
from app.services.jobs import (
    run_scrape,
    list_jobs,
    update_job,
    get_stats,
    mark_hot_jobs,
    get_hot_jobs,
)
from app.services.learning_paths import (
    create_default_learning_paths,
    get_learning_path,
    list_learning_paths,
    get_featured_learning_paths,
)
from app.services.notifications import notify_new_jobs, send_email_alert, send_slack_alert
from app.services.quality_trust import (
    detect_seniority,
    is_verified_remote,
    generate_duplicate_signature,
    detect_duplicates,
    calculate_source_performance,
    extract_salary_range,
)
from app.services.saved_searches import (
    create_saved_search,
    get_user_saved_searches,
    get_saved_search,
    update_saved_search,
    delete_saved_search,
    run_saved_search,
    saved_search_to_scrape_request,
)
from app.services.subscriptions import (
    get_or_create_subscription,
    upgrade_subscription,
    cancel_subscription,
    check_subscription_status,
    can_access_feature,
)

__all__ = [
    # Analytics
    "get_analytics_dashboard",
    "get_job_market_heatmap",
    "get_remote_hiring_trends",
    "get_salary_insights",
    "get_source_performance",
    "update_source_performance_metrics",
    # Auth
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "authenticate_user",
    "create_email_verification",
    "verify_email_code",
    "verify_email_token",
    "create_session",
    "get_session_by_token",
    "revoke_session",
    "revoke_all_user_sessions",
    "update_last_login",
    "create_or_update_oauth_user",
    # Companies
    "get_or_create_company",
    "update_company_from_job",
    "get_company_jobs",
    "get_company_stats",
    "list_all_companies",
    "search_companies",
    # Job Bundles
    "create_default_job_bundles",
    "list_job_bundles",
    "get_job_bundle",
    "get_featured_job_bundles",
    "increment_bundle_view",
    "increment_bundle_purchase",
    # Jobs
    "run_scrape",
    "list_jobs",
    "update_job",
    "get_stats",
    "mark_hot_jobs",
    "get_hot_jobs",
    # Learning Paths
    "create_default_learning_paths",
    "get_learning_path",
    "list_learning_paths",
    "get_featured_learning_paths",
    # Notifications
    "notify_new_jobs",
    "send_email_alert",
    "send_slack_alert",
    # Quality Trust
    "detect_seniority",
    "is_verified_remote",
    "generate_duplicate_signature",
    "detect_duplicates",
    "calculate_source_performance",
    "extract_salary_range",
    # Saved Searches
    "create_saved_search",
    "get_user_saved_searches",
    "get_saved_search",
    "update_saved_search",
    "delete_saved_search",
    "run_saved_search",
    "saved_search_to_scrape_request",
    # Subscriptions
    "get_or_create_subscription",
    "upgrade_subscription",
    "cancel_subscription",
    "check_subscription_status",
    "can_access_feature",
]