# To run the pipeline:
 
1. `pip install -r requirements.txt`

2. Get into the `paper_experiments` directory: `cd paper_experiments`

3. `python ClassifierAttributionTraining.py --model_name SpecResNet --audio_duration 7.5 --gpu 0`

4. Then run the testing classifications in order:

```
# Closed set classification
python Exp1_ClosedsetClassification.py --model_name SpecResNet --audio_duration 7.5 --gpu 0

# Open set classification (threshold)
python Exp2_OpenSetClassification_threshold.py --model_name SpecResNet --audio_duration 7.5 --gpu 0

# Open set classification (SVM)
python Exp3_OpenSetClassification_SVM.py --model_name SpecResNet --audio_duration 7.5 --gpu 0
```

5. Generate all the plots: `python plots_paper.py`