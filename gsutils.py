from google.cloud import storage
from generate_wav import Waveform



def upload_blob(bucket_name, source_wavefile, source_image, destination_wavefile_name, destination_image_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    # uploads both the wavefile and the wavefile image


    print("trying to upload blob", bucket_name, source_wavefile, source_image, destination_wavefile_name, destination_image_name)

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    wavefile_blob = bucket.blob(destination_wavefile_name)
    image_blob = bucket.blob(destination_image_name)

    wavefile_blob.upload_from_filename(source_wavefile)
    image_blob.upload_from_filename(source_image)

    print(
        "Files {} & {} uploaded".format(
            source_wavefile, source_image
        )
    )

def generate_wav(wav_file):
    waveform = Waveform(wav_file)
    waveform.save()
    return

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )