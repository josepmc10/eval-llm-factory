def calculate_classification_metrics(predictions: list, ground_truths: list) -> dict:
    """
    Calculates macro-averaged Accuracy, Precision, Recall, and F1-Score in pure Python.
    Normalizes string values by lowercase and strip to ensure robust matching.
    
    Args:
        predictions: List of model predictions.
        ground_truths: List of ground truths.
        
    Returns:
        dict: {
            "accuracy": float,
            "precision": float,
            "recall": float,
            "f1_score": float
        }
    """
    if not predictions or not ground_truths or len(predictions) != len(ground_truths):
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0
        }

    def normalize(val):
        if val is None:
            return ""
        return str(val).strip().lower()

    norm_preds = [normalize(p) for p in predictions]
    norm_gts = [normalize(gt) for gt in ground_truths]

    total = len(norm_gts)
    if total == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0}

    correct_count = sum(1 for p, gt in zip(norm_preds, norm_gts) if p == gt)
    accuracy = correct_count / total

    all_classes = set(norm_preds + norm_gts)
    if "" in all_classes:
        all_classes.remove("")
    
    if not all_classes:
        # Fallback if all values are empty
        return {
            "accuracy": accuracy,
            "precision": accuracy,
            "recall": accuracy,
            "f1_score": accuracy
        }

    precision_sum = 0.0
    recall_sum = 0.0
    f1_sum = 0.0

    for c in all_classes:
        tp = sum(1 for p, gt in zip(norm_preds, norm_gts) if p == c and gt == c)
        fp = sum(1 for p, gt in zip(norm_preds, norm_gts) if p == c and gt != c)
        fn = sum(1 for p, gt in zip(norm_preds, norm_gts) if p != c and gt == c)

        # Precision for class c
        if tp + fp > 0:
            p_c = tp / (tp + fp)
        else:
            p_c = 0.0
            
        # Recall for class c
        if tp + fn > 0:
            r_c = tp / (tp + fn)
        else:
            r_c = 0.0

        # F1-score for class c
        if p_c + r_c > 0:
            f1_c = 2 * (p_c * r_c) / (p_c + r_c)
        else:
            f1_c = 0.0

        precision_sum += p_c
        recall_sum += r_c
        f1_sum += f1_c

    num_classes = len(all_classes)
    macro_precision = precision_sum / num_classes
    macro_recall = recall_sum / num_classes
    macro_f1 = f1_sum / num_classes

    return {
        "accuracy": accuracy,
        "precision": macro_precision,
        "recall": macro_recall,
        "f1_score": macro_f1
    }
