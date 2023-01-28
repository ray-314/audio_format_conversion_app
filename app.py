"""
A web application that converts the sample rate of audio files.
"""

import streamlit as st
from pathlib import Path
import tempfile
import sox
import os
import pandas as pd
import time
from zipfile import ZipFile
import base64
from typing import Tuple

def validate_audio_path(input_filepath: str) -> Tuple[str, list[str]]:
    """Determine if the path is correct.

    Args:
        input_filepath (str): Input audio file path

    Returns:
        Tuple[str, list[str]]: Directory and audio file name list
    """
    if os.path.exists(input_filepath):
        if input_filepath[-1]=='/': input_filepath = input_filepath[:-1]
        if input_filepath[-4:]=='.wav':
            directory_path = input_filepath.rsplit('/', 1)[0] + '/'
            input_filename_list = [input_filepath.rsplit('/', 1)[1]]
        else:
            directory_path, input_filename_list = make_audio_list(input_filepath)
    else:
        directory_path = ''
        input_filename_list = []
    return directory_path, input_filename_list

def make_audio_list(input_filepath: str) -> Tuple[str, list[str]]:
    """Create directory path and audio file name list.

    Args:
        input_filepath (str): Input audio file path

    Returns:
        Tuple[str, list[str]]: Directory and audio file name list
    """
    directory_path = input_filepath + '/'
    try:
        input_filename_list = sorted([i for i in os.listdir(input_filepath) if i[-4:]=='.wav'])
    except:
        input_filename_list = []
    return directory_path, input_filename_list

@st.cache
def audio_info(input_filepath: str) -> dict:
    """Get audio file information.

    Args:
        input_filepath (str): Input audio file path

    Returns:
        dict: Audio file details
    """
    return sox.file_info.info(input_filepath)

@st.cache
def make_df(input_filename: str, input_data_info: dict) -> pd.DataFrame:
    """Create data frame.

    Args:
        input_filename (str): Input audio file path
        input_data_info (dict): Audio file details

    Returns:
        pd.DataFrame: Dataframe of audio file details
    """
    df = pd.DataFrame(input_data_info, index=[input_filename])
    return df

def make_directory(output_filepath: str) -> str:
    """Create output directory.

    Args:
        output_filepath (str): Destination directory

    Returns:
        str: The path where the "convert_samplerate" directory was created in the save destination directory
    """
    if os.path.isdir(output_filepath):
        if output_filepath[-1]!='/': output_filepath = output_filepath + '/'
        output_filepath = output_filepath + 'convert_samplerate' + '/'
        if not os.path.exists(output_filepath):
            os.mkdir(output_filepath)
    else:
        output_filepath = None
    return output_filepath

def convert_samplerate(sample_rate: str, input_filepath: str, output_filepath: str, file_name: str) -> None:
    """Convert the sample rate of audio data.

    Args:
        sample_rate (str): Sample rate
        input_filepath (str): Input audio file path
        output_filepath (str): Destination directory
        file_name (str): Audio file name
    """
    sample_frequency = {
        '11k': 11025, 
        '16k': 16000
    }
    output_filepath = output_filepath + file_name
    tfm = sox.Transformer()
    tfm.set_output_format(rate=sample_frequency[sample_rate])
    tfm.build_file(input_filepath=input_filepath, output_filepath=output_filepath)
    return None


def main():
    st.title('音声フォーマット変換アプリ')
    st.markdown('### 入力データの選択')
    input_option = st.selectbox(
        'ローカル上でStreamlitを動かしている場合のみ「パスの入力」が可能です',
        ('ファイルのアップロード', 'パスの入力'),
    )
    # setting
    input_filename_list = []
    uploaded_flag = False
    output_filepath = None

    try:
        # get directory path of audio files and list of audio filenames
        if input_option == 'パスの入力':
            directory_path, input_filename_list = validate_audio_path(st.text_input('こちらにWaveファイルのフルパスを入力してください。', 'sample/ohayo01shibu.wav'))
            input_filename_dict = dict(zip(input_filename_list, input_filename_list))
            if input_filename_list==[]:
                st.warning('指定されたパスには音声ファイルが存在しません')
        else:
            uploaded_files = st.file_uploader('Waveファイルを選択してください', type='wav', accept_multiple_files=True)
            uploaded_flag = True
            directory_path = tempfile.gettempdir()
            if directory_path[-1]!='/': directory_path = directory_path + '/'
            real_filename_list = []
            # temporarily save uploaded audio files
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    input_filepath = tmp_file.name
                    fp = Path(input_filepath)
                    fp.write_bytes(uploaded_file.getvalue())
                    real_filename_list.append(input_filepath.rsplit('/', 1)[1])
                    input_filename_list.append(uploaded_file.name)
            input_filename_dict = dict(zip(input_filename_list, real_filename_list))
    except:
        st.error('ファイルのアップロードもしくはパスの指定の不具合により、エラーが発生しました。リロードし直してください。')
        input_filename_list = []
        if uploaded_flag==True:
            for audio_file in real_filename_list:
                path = os.path.join(directory_path, audio_file)
                if os.path.exists(path):
                    os.remove(path)

    if input_filename_list!=[]:
        # view audio file details
        st.markdown('### 音声データの詳細')
        st.write('データ数 : {}'.format(len(input_filename_list)))
        select_name = st.selectbox(
            '入力データ : フォルダ内の音声データを選択してください',
            input_filename_list
        )
        select_data = input_filename_dict[select_name]
        with open(directory_path + select_data, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format='audio/wav')
            st.dataframe(make_df(select_name, audio_info(directory_path + select_data)))

        # specify sample rate
        st.markdown('### フォーマット変換')
        samplerate = st.selectbox(
            '変更後のサンプルレートを選択してください',
            ('11k', '16k'),
        )
        # set the save destination
        if uploaded_flag is not True:
            st.sidebar.markdown('### 保存先パスの設定')
            if st.sidebar.checkbox('保存先を入力パスと同じに設定する'):
                same_path = directory_path
                output_filepath = st.text_input('こちらに保存先のフルパスを入力してください。保存先に「convert_samplerate」フォルダが作成されます。', same_path)
            else:
                output_filepath = st.text_input('こちらに保存先のフルパスを入力してください。保存先に「convert_samplerate」フォルダが作成されます。', placeholder = 'output_directory_path')
        else:
            output_filepath = directory_path

        if output_filepath is not None:
            if st.button('Convert & Download'):
                try:
                    # change the sample rate of audio files
                    if uploaded_flag is not True:
                        # create output directory
                        output_filepath = make_directory(output_filepath)
                        if output_filepath is None: st.warning('正しい保存先のディレクトリを指定してください。')
                    comment = st.empty()
                    col1, col2 = st.columns(2)
                    time_count = col1.empty()
                    data_count = col2.empty()
                    comment.write('変換を開始します')
                    time_count.write('処理時間 : 0s or 0m')
                    data_count.write('処理済みのデータ数 : 0 / 0')

                    my_bar = st.progress(0)
                    start = time.time()
                    for count,audio_name in enumerate(input_filename_list):
                        convert_samplerate(sample_rate=samplerate, input_filepath=directory_path + input_filename_dict[audio_name], output_filepath=output_filepath, file_name = audio_name)
                        time_count.write('処理時間 : {}s or {}m'.format(round(time.time() - start), round((time.time() - start)/60, 2)))
                        data_count.write('処理済みのデータ数 : {} / {}'.format(count+1, len(input_filename_list)))
                        my_bar.progress((count + 1) / len(input_filename_list))
                    comment.success('完了しました')
                    
                    # view audio file details
                    st.markdown('### 変換後の音声データの詳細')
                    st.write('データ数 : {}'.format(count + 1))
                    with open(output_filepath + select_name, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/wav')
                        st.dataframe(make_df(select_name, audio_info(output_filepath + select_name)))
                    
                    if uploaded_flag is True:
                        # compress and save audio files
                        ZipfileDotZip = 'convert_samplerate.zip'
                        zipObj = ZipFile(directory_path + ZipfileDotZip, "w")
                        for count,audio_name in enumerate(input_filename_list):
                            zipObj.write(directory_path + audio_name , audio_name)
                        zipObj.close()

                        with open(directory_path + ZipfileDotZip, "rb") as f:
                            bytes = f.read()
                            b64 = base64.b64encode(bytes).decode()
                            href = f"<a href=\"data:file/zip;base64,{b64}\" download='{ZipfileDotZip}'>Click to download zip</a>"
                        st.sidebar.markdown('### 変換後の音声データのダウンロード')
                        st.sidebar.markdown('convert_samplerate.zipファイルをダウンロードしてください。')
                        st.sidebar.markdown(href, unsafe_allow_html=True)
                    else:
                        comment.success('ダウンロードが完了しました')
                except:
                    st.error('停止しました。やり直したい場合はリロードしてください。')
                finally:
                    if uploaded_flag==True:
                        for audio_file in (real_filename_list + input_filename_list):
                            path = os.path.join(directory_path, audio_file)
                            if os.path.exists(path):
                                os.remove(path)
        

if __name__=='__main__':
    main()