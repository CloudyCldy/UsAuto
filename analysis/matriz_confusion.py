import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix


def crear_matriz_confusion(y_true, y_pred, title='Matriz de confusión', filename=None):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['No compra', 'Compra'], yticklabels=['No compra', 'Compra'], ax=ax)
    ax.set_title(title)
    ax.set_xlabel('Predicción')
    ax.set_ylabel('Real')
    fig.tight_layout()
    plt.close(fig)
    return cm
