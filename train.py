from ultralytics import YOLO

def main():
    # Load a pretrained YOLOv8 nano model
    model = YOLO("yolov8n.pt")

    # Train the model
    # Note: You need to have your dataset downloaded locally and a dataset.yaml configured.
    print("Starting training...")
    
    # Replace 'dataset.yaml' with the actual path to your dataset configuration
    dataset_yaml_path = "dataset.yaml" 
    
    try:
        model.train(
            data=dataset_yaml_path,
            epochs=20,
            imgsz=640
        )
        print("Training complete! Your trained model will be saved in runs/detect/train/weights/best.pt")
    except Exception as e:
        print(f"Error during training: {e}")
        print("Ensure your dataset.yaml is correctly configured and the dataset is present locally.")

if __name__ == "__main__":
    main()
