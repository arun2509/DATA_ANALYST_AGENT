import pandas as pd
import re
import json
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns

def analyze_films(url):
    results = [None, None, None, None] # Initialize results array with None for each answer

    try:
        # 2. Scraping: Use pandas.read_html to read all tables
        # Use html5lib for robustness with malformed HTML
        tables = pd.read_html(url, flavor='html5lib')
    except Exception as e:
        results[0] = f"Error: Could not read tables from URL. {str(e)}"
        return json.dumps(results)

    best_df = pd.DataFrame()
    best_score = -1

    # Keywords for column matching (case-insensitive and partial matching)
    rank_keywords = ['rank']
    title_keywords = ['film', 'title', 'movie', 'name']
    gross_keywords = ['gross', 'revenue', 'box office']
    year_keywords = ['year', 'release', 'date', 'premiered']
    peak_keywords = ['peak']

    for df in tables:
        # Normalize column names: strip spaces, remove footnotes, convert to lowercase.
        normalized_columns = []
        for col in df.columns:
            # Handle MultiIndex columns if they exist
            if isinstance(col, tuple):
                col = ' '.join(col).strip()
            col = re.sub(r'\[\d+\]', '', str(col)).strip().lower()
            normalized_columns.append(col)
        df.columns = normalized_columns

        current_score = 0
        found_cols = {}

        # Match columns using partial/keyword matching
        for col in df.columns:
            if any(keyword in col for keyword in rank_keywords):
                found_cols['rank'] = col
                current_score += 1
            if any(keyword in col for keyword in title_keywords):
                found_cols['title'] = col
                current_score += 1
            if any(keyword in col for keyword in gross_keywords):
                found_cols['gross'] = col
                current_score += 1
            if any(keyword in col for keyword in year_keywords):
                found_cols['year'] = col
                current_score += 1
            if any(keyword in col for keyword in peak_keywords):
                found_cols['peak'] = col
                current_score += 1

        # Choose the table with the most relevant columns.
        # We need 'rank', 'title', 'gross', 'year', and 'peak' for all questions.
        if current_score > best_score and all(k in found_cols for k in ['rank', 'title', 'gross', 'year', 'peak']):
            best_df = df
            best_score = current_score
            best_df._found_cols = found_cols # Store the actual column names found

    if best_df.empty or best_score < 5: # Ensure we found all required columns
        results[0] = "Error: No suitable table with all required columns (Rank, Title, Gross, Year, Peak) found."
        return json.dumps(results)

    # Extract actual column names from the best found table
    rank_col = best_df._found_cols.get('rank')
    title_col = best_df._found_cols.get('title')
    gross_col = best_df._found_cols.get('gross')
    year_col = best_df._found_cols.get('year')
    peak_col = best_df._found_cols.get('peak')

    # Data Cleaning
    df_cleaned = best_df.copy()

    # Clean Gross column: remove symbols, commas, footnotes, convert to float
    def clean_gross(text):
        if pd.isna(text):
            return np.nan
        text = str(text).lower()
        text = re.sub(r'[$,\[\]\(\)]', '', text) # Remove currency symbols, brackets, parentheses
        text = re.sub(r'\[\d+\]', '', text) # Remove footnotes like [1]
        text = text.replace('approx.', '').strip() # Remove "approx."

        # Handle "billion" and "million" suffixes
        if 'billion' in text:
            value = float(text.replace('billion', '').strip()) * 1_000_000_000
        elif 'million' in text:
            value = float(text.replace('million', '').strip()) * 1_000_000
        else:
            # Try to convert directly, assuming it's already a number or has commas
            text = text.replace(',', '')
            try:
                value = float(text)
            except ValueError:
                value = np.nan
        return value

    df_cleaned['cleaned_gross'] = df_cleaned[gross_col].apply(clean_gross)

    # Clean Year column: extract 4-digit year
    def clean_year(text):
        if pd.isna(text):
            return np.nan
        text = str(text)
        # Look for a 4-digit number that typically represents a year (19xx or 20xx)
        match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if match:
            return int(match.group(0))
        return np.nan

    df_cleaned['cleaned_year'] = df_cleaned[year_col].apply(clean_year)

    # Clean Rank and Peak columns: remove non-numeric characters, convert to int
    def clean_numeric(text):
        if pd.isna(text):
            return np.nan
        text = str(text)
        text = re.sub(r'[^0-9]', '', text) # Keep only digits
        try:
            return int(text)
        except ValueError:
            return np.nan

    df_cleaned['cleaned_rank'] = df_cleaned[rank_col].apply(clean_numeric)
    df_cleaned['cleaned_peak'] = df_cleaned[peak_col].apply(clean_numeric)

    # Drop rows with NaN in critical columns after cleaning to ensure valid data for calculations
    df_cleaned.dropna(subset=['cleaned_gross', 'cleaned_year', 'cleaned_rank', 'cleaned_peak'], inplace=True)

    # Ensure numeric types for calculations
    df_cleaned['cleaned_gross'] = df_cleaned['cleaned_gross'].astype(float)
    df_cleaned['cleaned_year'] = df_cleaned['cleaned_year'].astype(int)
    df_cleaned['cleaned_rank'] = df_cleaned['cleaned_rank'].astype(int)
    df_cleaned['cleaned_peak'] = df_cleaned['cleaned_peak'].astype(int)

    # --- Answer Question 1: How many $2 bn movies were released before 2000? ---
    try:
        two_bn_movies_before_2000 = df_cleaned[
            (df_cleaned['cleaned_gross'] >= 2_000_000_000) &
            (df_cleaned['cleaned_year'] < 2000)
        ].shape[0]
        results[0] = str(two_bn_movies_before_2000)
    except Exception as e:
        results[0] = f"Error calculating $2bn movies before 2000: {str(e)}"

    # --- Answer Question 2: Which is the earliest film that grossed over $1.5 bn? ---
    try:
        over_1_5_bn_movies = df_cleaned[df_cleaned['cleaned_gross'] >= 1_500_000_000]
        if not over_1_5_bn_movies.empty:
            # Find the row with the minimum year
            earliest_1_5_bn_movie = over_1_5_bn_movies.loc[over_1_5_bn_movies['cleaned_year'].idxmin()]
            results[1] = earliest_1_5_bn_movie[title_col]
        else:
            results[1] = "No film grossed over $1.5 billion."
    except Exception as e:
        results[1] = f"Error finding earliest $1.5bn movie: {str(e)}"

    # --- Answer Question 3: What's the correlation between the Rank and Peak? ---
    try:
        if not df_cleaned[['cleaned_rank', 'cleaned_peak']].empty:
            correlation = df_cleaned['cleaned_rank'].corr(df_cleaned['cleaned_peak'])
            results[2] = str(round(correlation, 4)) # Round to 4 decimal places
        else:
            results[2] = "Not enough data to calculate correlation."
    except Exception as e:
        results[2] = f"Error calculating correlation: {str(e)}"

    # --- Answer Question 4: Draw a scatterplot of Rank and Peak along with a dotted red regression line through it. ---
    try:
        if not df_cleaned[['cleaned_rank', 'cleaned_peak']].empty:
            plt.figure(figsize=(6, 4)) # Set figure size to keep image under 100KB
            sns.regplot(x='cleaned_rank', y='cleaned_peak', data=df_cleaned,
                        scatter_kws={'s': 20, 'alpha': 0.7}, # Smaller points, slight transparency
                        line_kws={'color': 'red', 'linestyle': ':'}) # Dotted red regression line
            plt.title('Rank vs. Peak Grossing Films')
            plt.xlabel('Rank')
            plt.ylabel('Peak')
            plt.grid(True, linestyle='--', alpha=0.6) # Add a grid for better readability
            plt.tight_layout() # Adjust layout to prevent labels from overlapping

            # Save plot to a BytesIO object and encode as base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100) # Lower DPI to reduce file size
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close() # Close the plot to free memory

            results[3] = f"data:image/png;base64,{image_base64}"
        else:
            results[3] = "Not enough data to generate scatterplot."
    except Exception as e:
        results[3] = f"Error generating scatterplot: {str(e)}"

    # Output contract: Print exactly one JSON array of strings
    return json.dumps(results)

# The URL for the Wikipedia page
url = "https://en.wikipedia.org/wiki/List_of_highest-grossing_films"

# Call the function and print the result
print(analyze_films(url))