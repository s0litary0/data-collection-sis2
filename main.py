from src.api_client import run_collect
from src.producer import run_producer
from src.consumer import run_consumer
from src.validator import run_validation
from src.cleaner import run_cleaning
from src.loader import run_loading
from src.reader import run_read
from src.analysis import run_analysis


def main():
    """Project entry point"""
    print("1. Data Source Selection and Collection")
    run_collect()
    print("2.1 Producer")
    run_producer()
    print("2.2 Consumer")
    records = run_consumer()
    print("3. Data Validation with Pandera")
    valid_df, _ = run_validation(records=records)
    print("4. Data Cleaning and Transformation")
    clean_df = run_cleaning(df=valid_df)
    print("5. Database Storage with SQLite3")
    run_loading(clean_df=clean_df)
    print("6. Exploratory Data Analysis and Visualization")
    df_from_db = run_read()
    run_analysis(df_from_db)
    


if __name__ == "__main__":
    main()
