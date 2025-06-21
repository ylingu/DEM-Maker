import logging
import os
import shutil
import subprocess

class PlyService:
    def __init__(self, working_dir='tello'):
        self.working_dir = working_dir
        self.colmap_exe = os.path.abspath(os.path.join("..","colmap","bin","colmap.exe"))

        # 配置日志
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def delete_file(self,file_path):
        """删除指定文件"""
        if os.path.exists(file_path):
            self.logger.info(f"删除文件: {file_path}")
            os.remove(file_path)
        else:
            self.logger.warning(f"文件不存在: {file_path}")

    def delete_folder(self,folder_path):
        """删除指定文件夹及其内容"""
        if os.path.exists(folder_path):
            self.logger.info(f"删除文件夹: {folder_path}")
            shutil.rmtree(folder_path)
        else:
            self.logger.warning(f"文件夹不存在: {folder_path}")

    def run_command(self,command):
        """运行命令并打印输出"""
        self.logger.info(f"运行命令: {command}")
        try:
            result = subprocess.run(
                command, shell=False, text=True, capture_output=True, check=True
            )
            self.logger.info(result.stdout)
            if result.stderr:
                self.logger.error(result.stderr)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"命令执行失败: {e}")
            self.logger.error(f"stdout:\n{e.stdout}")
            self.logger.error(f"stderr:\n{e.stderr}")
            raise

    def run_command2(self,command):
        """运行命令并打印输出"""
        self.logger.info(f"运行命令: {command}")
        try:
            result = subprocess.run(
                command, shell=True, text=True, capture_output=True, check=True
            )
            self.logger.info(result.stdout)
            if result.stderr:
                self.logger.error(result.stderr)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"命令执行失败: {e}")
            self.logger.error(f"stdout:\n{e.stdout}")
            self.logger.error(f"stderr:\n{e.stderr}")
            raise

    def run_colmap(self):
        """运行 COLMAP 相关命令"""
        os.makedirs(os.path.join(self.working_dir, "sparse"), exist_ok=True)
        
        self.run_command([
            self.colmap_exe,
            "feature_extractor",
            "--database_path", os.path.join(self.working_dir, "database.db"),
            "--image_path", os.path.join(self.working_dir, "images"),
            "--ImageReader.single_camera", "1"
        ])
    
        self.run_command([
            self.colmap_exe,
            "exhaustive_matcher",
            "--database_path", os.path.join(self.working_dir, "database.db")
        ])
        
        self.run_command([
            self.colmap_exe,
            "mapper",
            "--database_path", os.path.join(self.working_dir, "database.db"),
            "--image_path", os.path.join(self.working_dir, "images"),
            "--output_path", os.path.join(self.working_dir, "sparse")
        ])

    def generate_colmap_input(self):
        """生成 COLMAP 输入"""
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ply/colmap_input.py"))
        self.run_command2(f"python {script_path} --input_folder {self.working_dir} --output_folder {self.working_dir}/colmap_input")
    
    def run_evaluation(self):
        """运行评估脚本"""
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ply/eval.py"))
        ckpt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ply/checkpoints/params_000007.ckpt"))
        self.run_command2(f"python {script_path} --input_folder {self.working_dir}/colmap_input --output_folder {self.working_dir}/colmap_input/depths --checkpoint_path {ckpt_path} --num_view 5")
    
    def main(self):
        """主函数，整合所有步骤"""
        # 设置工作目录
        os.chdir(self.working_dir)

        # 删除旧的文件夹和数据库
        self.delete_folder("sparse")
        self.delete_folder("colmap_input")
        self.delete_file("database.db")

        # 执行各步骤
        self.run_colmap()
        self.generate_colmap_input()
        self.run_evaluation()
        return f"点云生成完成，结果保存在 {self.working_dir}"
