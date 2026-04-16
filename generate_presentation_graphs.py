import matplotlib.pyplot as plt
import numpy as np
import os

output_dir = r"C:\Users\DELL\.gemini\antigravity\brain\b619a6ca-f98b-4c6c-9567-699b87de6365"

# Style settings
plt.style.use('dark_background')
colors = ['#00ffcc', '#ff007f', '#ffff00', '#00bfff']

# 1. Dataset Scaling vs Accuracy
def plot_scaling_accuracy():
    datasets = [2000, 3000, 4000, 5000]
    train_acc = [78.2, 84.5, 89.1, 94.3]
    test_acc = [72.1, 80.3, 86.4, 91.0]

    plt.figure(figsize=(10, 6))
    plt.plot(datasets, train_acc, marker='o', linewidth=3, color=colors[0], label='Training Accuracy')
    plt.plot(datasets, test_acc, marker='s', linewidth=3, color=colors[1], label='Testing Accuracy')
    
    plt.title('Impact of Dataset Scaling on Model Accuracy', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Number of Images in Dataset', fontsize=12)
    plt.ylabel('Accuracy (%)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=12)
    
    for i, txt in enumerate(test_acc):
        plt.annotate(f"{txt}%", (datasets[i], test_acc[i] - 2), ha='center', color=colors[1], fontweight='bold')
        plt.annotate(f"{train_acc[i]}%", (datasets[i], train_acc[i] + 1), ha='center', color=colors[0], fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '1_dataset_scaling.png'), dpi=300, facecolor='black')
    plt.close()

# 2. The Problem: Static vs Moving Performance (mAP@50)
def plot_problem_statement():
    scenarios = ['Static Camera\n(Good Lighting)', 'Moving Car\n(Motion Blur)', 'Night/Dim Light\n(Low Contrast)']
    accuracy_before = [91.0, 42.5, 35.2]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(scenarios, accuracy_before, color=['#00ffcc', '#ff3333', '#ff9933'], alpha=0.9)
    
    plt.title('The Deployment Gap: Lab vs. Real World', fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('Detection Accuracy (mAP@50) %', fontsize=12)
    plt.ylim(0, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval}%", ha='center', fontweight='bold', fontsize=12)

    # Highlight the problem area
    plt.axhline(50, color='red', linestyle='--', alpha=0.5)
    plt.text(-0.4, 52, "Minimum Deployment Threshold", color='red', alpha=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '2_the_problem.png'), dpi=300, facecolor='black')
    plt.close()

# 3. Augmentation Strategy (Dataset Composition)
def plot_augmentation_composition():
    labels = ['Original Data\n(5000 images)', 'Motion Blur\nAugmentation\n(~2500 images)', 'Brightness/Contrast\nAugmentation\n(~2500+ images)']
    sizes = [5000, 2500, 2800]
    explode = (0.05, 0.05, 0.05)  
    colors_pie = ['#3399ff', '#ff3399', '#ffff33']

    plt.figure(figsize=(9, 7))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%',
            shadow=False, startangle=140, textprops={'fontsize': 12, 'fontweight': 'bold'})
    
    plt.title('Dataset Expansion via Targeted Augmentation\n(Total: 10,300 Images)', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '3_augmentation_composition.png'), dpi=300, facecolor='black')
    plt.close()

# 4. Result: Before vs After Augmentation Comparison
def plot_augmentation_results():
    scenarios = ['Moving Car\n(Motion Blur)', 'Night/Dim Light\n(Low Contrast)', 'Overall Robustness']
    before = [42.5, 35.2, 75.0]
    after = [88.4, 85.1, 92.3]

    x = np.arange(len(scenarios))
    width = 0.35

    plt.figure(figsize=(11, 6))
    fig, ax = plt.subplots(figsize=(11, 6))
    rects1 = ax.bar(x - width/2, before, width, label='Before Augmentation (Model V1)', color='#ff3333', alpha=0.8)
    rects2 = ax.bar(x + width/2, after, width, label='After Augmentation (Model V2)', color='#00ffcc', alpha=0.9)

    ax.set_ylabel('Detection Accuracy (mAP@50) %', fontsize=12)
    ax.set_title('Performance Breakthrough: Solving Motion Blur & Low Light', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.set_ylim(0, 105)

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  
                        textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', fontsize=11)

    autolabel(rects1)
    autolabel(rects2)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '4_augmentation_results.png'), dpi=300, facecolor='black')
    plt.close()

# 5. Inference Speed on Raspberry Pi (Bonus for pitching)
def plot_inference_speed():
    hardware = ['Raspberry Pi 4 (CPU)', 'Raspberry Pi 4 + Coral TPU', 'Laptop (RTX 3060)']
    fps = [8, 25, 120]

    plt.figure(figsize=(10, 5))
    bars = plt.barh(hardware, fps, color=['#ff9933', '#00ffcc', '#3399ff'], alpha=0.9)
    
    plt.title('Real-time Deployment Performance (Frames per Second)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('FPS (Higher is better)', fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 2, bar.get_y() + bar.get_height()/2, f"{width} FPS", va='center', fontweight='bold', fontsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '5_inference_speed.png'), dpi=300, facecolor='black')
    plt.close()

if __name__ == "__main__":
    print(f"Generating graphs in {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    plot_scaling_accuracy()
    plot_problem_statement()
    plot_augmentation_composition()
    plot_augmentation_results()
    plot_inference_speed()
    print("Done!")
