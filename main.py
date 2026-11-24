from src.api_client import run_collect
from src.producer import run_producer
from src.consumer import run_consumer
from src.validator import run_validation
from src.cleaner import run_cleaning


def main():
    """Project entry point"""
    print("1. Data Source Selection and Collection")
    run_collect()
    print("2.1 Producer")
    run_producer()
    print("2.2 Consumer")
    records = run_consumer()
    print("3. Data Validation with Pandera")
    valide_df, _ = run_validation(records=records)
    print("4. Data Cleaning and Transformation")
    run_cleaning(df=valide_df)


if __name__ == "__main__":
    main()
