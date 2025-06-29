
import csv
import re

def process_sources():
    with open('docs/rick_rubin_sources.md', 'r') as f:
        sources = f.readlines()

    with open('data/rick_rubin_source_analysis.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        for i, source in enumerate(sources):
            if i < 10:
                match = re.search(r'\[(.*?)\]\((.*?)\)', source)
                if match:
                    title = match.group(1)
                    url = match.group(2)
                    source_type = "Unknown"
                    if "article" in title.lower() or "news" in title.lower() or "guide" in title.lower() or "history" in title.lower() or "insights" in title.lower() or "review" in title.lower():
                        source_type = "Article"
                    elif "podcast" in title.lower():
                        source_type = "Podcast"
                    elif "interview" in title.lower():
                        source_type = "Interview"
                    elif "book" in title.lower():
                        source_type = "Book"

                    # Placeholder values for quality, relevance, accessibility, and licensing
                    quality = "High"
                    relevance = 5
                    accessibility = "Publicly available"
                    licensing = "Copyrighted, educational/research use likely acceptable. Commercial use requires license."

                    writer.writerow([title, url, source_type, quality, relevance, accessibility, licensing])

if __name__ == "__main__":
    process_sources()
