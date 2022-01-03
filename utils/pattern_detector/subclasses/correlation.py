from scipy import stats

class Correlation:
    GRADE = {"CONSTANT":0, "NEGATIVE":1, "NEGLIGIBLE":2, "POSITIVE":3, "OBVIOUS_POSITIVE":4, "STRONG_POSITIVE":5, "PERFECT_POSITIVE":6}
    
    CONSTANT = "CONSTANT"
    NEGATIVE = "NEGATIVE"
    NEGLIGIBLE = "NEGLIGIBLE"
    POSITIVE = "POSITIVE"
    OBVIOUS_POSITIVE = "OBVIOUS_POSITIVE"
    STRONG_POSITIVE = "STRONG_POSITIVE"
    PERFECT_POSITIVE = "PERFECT_POSITIVE"

    def __init__(self, base_set, comp_set, max_check=False):
        self.base_set = base_set
        self.comp_set = comp_set
        self.spearman, self.s_pvalue = self.calculate_spearman_correlation(comp_set)
        self.pearson, self.p_pvalue = self.calculate_pearson_correlation(comp_set)
        self.grade = Correlation.get_correlation_grade(self.spearman)
        self.grade_str = Correlation.get_correlation_grade_str(self.spearman)

        self.max_check = max_check

    def calculate_spearman_correlation(self, opc_remain):
        if len(set(opc_remain)) == 1:
            return 0, 0

        result = stats.spearmanr(self.base_set, opc_remain)
        spearman = result[0]
        pvalue = result[1]

        if spearman > 0.99999:
            return 1, pvalue

        return spearman, pvalue

    def calculate_pearson_correlation(self, opc_remain):
        if len(set(opc_remain)) == 1:
            return 0, 0

        result = stats.pearsonr(self.base_set, opc_remain)
        spearman = result[0]
        pvalue = result[1]

        if spearman > 0.99999:
            return 1, pvalue

        return spearman, pvalue

    def get_correlation_grade_str(correlation):
        if correlation is None:
            return None
        elif correlation == 0:
            return Correlation.CONSTANT
        elif correlation < 0:
            return Correlation.NEGATIVE
        elif correlation < 0.3:
            return Correlation.NEGLIGIBLE
        elif correlation == 1:
            return Correlation.PERFECT_POSITIVE
        elif correlation >= 0.9:
            return Correlation.STRONG_POSITIVE
        elif correlation >= 0.7:
            return Correlation.OBVIOUS_POSITIVE
        else:
            return Correlation.POSITIVE

    def get_correlation_grade(correlation):
        if correlation is None:
            return None
        elif correlation == 0:
            return Correlation.GRADE[Correlation.CONSTANT]
        elif correlation < 0:
            return Correlation.GRADE[Correlation.NEGATIVE]
        elif correlation < 0.3:
            return Correlation.GRADE[Correlation.NEGLIGIBLE]
        elif correlation == 1:
            return Correlation.GRADE[Correlation.PERFECT_POSITIVE]
        elif correlation >= 0.9:
            return Correlation.GRADE[Correlation.STRONG_POSITIVE]
        elif correlation >= 0.7:
            return Correlation.GRADE[Correlation.OBVIOUS_POSITIVE]
        else:
            return Correlation.GRADE[Correlation.POSITIVE]
