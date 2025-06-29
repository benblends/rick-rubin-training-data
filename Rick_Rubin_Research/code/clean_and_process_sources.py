
import pandas as pd

def clean_and_process_sources():
    """
    Reads the raw source analysis CSV, cleans and processes the data,
    and saves it to a new CSV file.
    """
    try:
        # Read the raw data
        df = pd.read_csv("data/rick_rubin_source_analysis.csv")

        # 1. Remove duplicate URLs
        df.drop_duplicates(subset=["URL"], keep="first", inplace=True)

        # 2. Fix Categorization and Assign Priority
        def categorize_and_prioritize(row):
            title = str(row["Source"]).lower()
            url = str(row["URL"]).lower()
            
            # Tier 1: Core, primary sources from Rubin himself
            if "the creative act" in title:
                return "Book (Authored)", 1
            if "tetragrammaton" in title or "broken record" in title:
                return "Podcast (Host)", 1
            
            # Tier 2: High-quality interviews and direct conversations
            if "interview" in title or "conversation" in title or "inurl:interview" in url:
                return "Interview", 2
            if "podcast" in title:
                return "Podcast (Guest)", 2

            # Tier 3: Secondary analysis, articles, and data
            if "article" in title or "guide" in title or "history" in title or "review" in title:
                return "Article", 3
            if "credits" in title or "discography" in title or "allmusic" in url:
                return "Database/Credits", 3
            if ".edu" in url or ".ac" in url:
                return "Academic/Scholarly", 3

            return row["Source Type"], 4 # Default for anything uncategorized

        df[["Source Type", "Priority"]] = df.apply(categorize_and_prioritize, axis=1, result_type="expand")

        # 3. Sort by priority and then by type
        df.sort_values(by=["Priority", "Source Type"], inplace=True)
        
        # 4. Save the cleaned data
        df.to_csv("data/cleaned_rick_rubin_sources.csv", index=False)
        
        print("Successfully cleaned and processed the source data.")
        print(f"Removed duplicates. Original count: {len(pd.read_csv('data/rick_rubin_source_analysis.csv'))}, Cleaned count: {len(df)}")
        print("\nSource Type Distribution:")
        print(df["Source Type"].value_counts())

    except FileNotFoundError:
        print("Error: data/rick_rubin_source_analysis.csv not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clean_and_process_sources()
