import pandas as pd
import re

class ColumnSuggester:
    KEYWORDS = {
        'matricola': ['matricola', 'matr', 'cod.dip'],
        'nominativo': ['cognome e nome', 'lavoratore', 'nominativo'],
        'paga_base': ['minimo', 'lordo', 'base', 'retribuzione di fatto'],
    }

    def suggest_columns(self, df):
        suggestions = {}
        header_sample = df.iloc[:3].fillna('').astype(str).values.tolist()
        for col_idx in range(len(df.columns)):
            combined_text = " ".join([row[col_idx] for row in header_sample]).lower()
            for field, keys in self.KEYWORDS.items():
                if any(k in combined_text for k in keys):
                    suggestions[col_idx] = field
                    break
        return suggestions