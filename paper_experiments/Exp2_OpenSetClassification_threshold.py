import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
import sys
sys.path.append('../')
import data_lib
import os
import torch
import params
import network_models_lib
import argparse
import copy
import numpy as np
import matplotlib.pyplot as plt
import params
from sklearn.metrics import f1_score, balanced_accuracy_score, confusion_matrix, ConfusionMatrixDisplay
from tqdm import tqdm
from data_lib import SUNOCAPS_PATH, model_labels, MusicDeepFakeDataset, test_suno
def number_of_correct(pred, target):
    # count number of correct predictions
    return pred.squeeze().eq(target).sum().item()
def get_likely_index_openset(tensor, OpenClassLabel, thresh):
    # find most likely label index for each element in the batch
    pred = tensor.argmax(dim=-1)

    tensor = tensor.detach().cpu()  # Model uses LogSoftmax
    # Check thresholding

    #N.B. we are working with logarithms --> division = subtraction
    for o_idx in range(len(tensor)):
        values, _ = torch.sort(tensor[o_idx, 0], descending=True)
        if values[0] - values[1] < torch.log(torch.Tensor([thresh])):
            pred[o_idx] = OpenClassLabel

    return pred

parser = argparse.ArgumentParser(description='OSCLassification')
parser.add_argument('--gpu', type=str, help='gpu', default='0')
parser.add_argument('--model_name', type=str, default='SpecResNet')
parser.add_argument('--audio_duration', type=float, help='Length of the audio slice in seconds',
                    default=7.5)
args = parser.parse_args()

print('Open set (threshold)considering model {}'.format(args.model_name))
for args.audio_duration in [7.5]:
    print('Audio duration {}'.format(args.audio_duration))
    # Model selection
    if args.model_name == 'M5':
        model = network_models_lib.M5(n_input=1, n_output=len(data_lib.model_labels))
        lr = 0.001
        feat_type = 'raw'
    elif args.model_name == 'RawNet2':
        d_args = {"nb_samp": int(args.audio_duration * params.DESIRED_SR), "first_conv": 3, "in_channels": 1,
                  "filts": [128, [128, 128], [128, 256], [256, 256]],
                  "blocks": [2, 4], "nb_fc_node": 1024, "gru_node": 1024, "nb_gru_layer": 1,
                  "nb_classes": len(data_lib.model_labels)}
        lr = 0.0001
        print('USING MODEL {}'.format(args.model_name))
        model = network_models_lib.RawNet2(d_args)
        feat_type = 'raw'
    elif args.model_name == 'SpecResNet':
        lr = 0.0001
        print('USING MODEL {}'.format(args.model_name))
        model = network_models_lib.ResNet(img_channels=1, num_layers=18, block=network_models_lib.BasicBlock,
                                          num_classes=len(data_lib.model_labels))
        feat_type = 'freq'
    model.load_state_dict(torch.load( os.path.join(params.PARENT_DIR,'models','{}_duration_{}_secs.pth'.format(args.model_name, round(args.audio_duration,1))), weights_only=True))



    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    OpenClassLabel = 6
    test_suno_files = [os.path.join(SUNOCAPS_PATH,path) for path in test_suno]
    model_labels_open_set = copy.deepcopy(model_labels)
    model_labels_open_set.update({'SunoCaps': OpenClassLabel})
    test_open_data = MusicDeepFakeDataset(test_suno_files+data_lib.test_files, model_labels_open_set, args.audio_duration,feat_type=feat_type) # ERROR
    test_open_dataloader = torch.utils.data.DataLoader(test_open_data, batch_size=1, shuffle=True,num_workers=1)


    # Thresholding
    thresh = 2
    correct = 0
    pred_list = []
    target_list = []
    for data, target in test_open_dataloader:
        data = data.to(device)
        target = target.to(device)

        # apply transform and model on whole batch directly on device
        output = model(data)

        #print('TARGET {}'.format(target))
        # For Accuracy
        pred = get_likely_index_openset(output,OpenClassLabel,thresh)
        correct += number_of_correct(pred.squeeze(), target.squeeze())

        # For confusion matrix
        pred_list = pred_list + pred.cpu().numpy()[:, 0].tolist()
        target_list = target_list +target.cpu().to(torch.int64).numpy()[:, 0].tolist()
        # update progress bar
        #pbar.update(pbar_update)

    cm = confusion_matrix(target_list, pred_list, normalize='true')
    np.save(os.path.join(params.PARENT_DIR,'figures/cm_open_set_thresh_{}_{}_sec.npy'.format(args.model_name,args.audio_duration)),cm)

    disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                                  display_labels=[r'REAL', r'TTM01', r'TTM02', r'TTM03', r'TTM04', r'TTM05',r'UNKWN'])
    # Enable LaTeX rendering - commented out for now
    # plt.rcParams['text.usetex'] = True
    # Adjust global font sizes
    # Plot confusion matrix
    disp.plot(cmap=plt.cm.Blues,colorbar=False)
    # Customize tick labels and axis labels to use LaTeX
    plt.xticks(rotation=45)
    plt.xlabel(r'Predicted Labels', fontsize=15)
    plt.ylabel(r'True Labels', fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(params.PARENT_DIR, 'figures', f'cm_open_set_thresh_{args.model_name}_{args.audio_duration}_sec.png'), dpi=300)
    plt.show()

    # Balanced accuracy score
    ACC_B = balanced_accuracy_score(target_list, pred_list)
 
    # Precision
    precision_classes = np.zeros(len(data_lib.models_names)+1)
    occurrence_classes = np.zeros(len(data_lib.models_names)+1)

    for idx in range(len(pred_list)):
        occurrence_classes[pred_list[idx]] += 1
        if pred_list[idx] == target_list[idx]:
            precision_classes[target_list[idx]] += 1
    precision_classes /= occurrence_classes
    precision_tot = np.mean(precision_classes)



    # Recall
    recall_classes = np.zeros(len(data_lib.models_names)+1)
    occurrence_classes_recall = np.zeros(len(data_lib.models_names)+1)

    for idx in range(len(pred_list)):
        occurrence_classes_recall[target_list[idx]] += 1
        if pred_list[idx] == target_list[idx]:
            recall_classes[target_list[idx]] += 1
    recall_classes /= occurrence_classes_recall
    recall_tot = np.mean(recall_classes)

    # F1-score
    F1_per_class = f1_score(target_list, pred_list, average=None)
    F1_avg = f1_score(target_list, pred_list, average='macro')

    results = np.array([round(ACC_B, 2), round(precision_tot, 2), round(recall_tot, 2),  round(F1_avg, 2)])
    results_filename = os.path.join(params.PARENT_DIR,'results','open_set_thresh__{}_{}_sec.npy'.format(args.model_name,
                                                                                                  args.audio_duration))
    np.save(results_filename, results)

    #print('Open Set prediction')
    print('ACC_B: {} Precision {} Recall {}'
          ' F1 Score {}'.format(round(ACC_B, 2),
                                round(precision_tot, 2),
                                round(recall_tot, 2),
                                round(F1_avg, 2)))

