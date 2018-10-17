# encoding=utf-8
import configparser
import datetime
import time
from concurrent import futures

import paramiko, os
from collections import namedtuple
import pysftp
import json

Project = namedtuple("Project", "name backupFile localPath remoteTargetPath")

shopIdList = []


class UpgradeConf:

    def __init__(self, config_file_name):
        config = configparser.ConfigParser()
        config.read(config_file_name)
        BACKUP_PATH = config.get('remote', 'backup_path')
        upgrade_project = config.get('global', 'project_name').split(',')

        self.PORT = config.get('remote', 'port')
        self.USER = config.get('remote', 'username')
        self.PASSWORD = config.get('remote', 'password')
        self.WEBAPP_PATH = config.get('remote', 'webapp_path')
        self.UPGRADE_PATH = config.get('remote', 'pre_upgrade_path')

        self.shopIdList = config.get('global', 'shop_id').split(',')

        self.LOCAL_UPGRADE_FILE = config.get('local', 'project_dir')
        self.backup_commend = "cd /app && cp -r webapp/{PROJECT_NAME} " + BACKUP_PATH \
                              + "/{BACKUP_PROJECT} && cp -r webapp/{PROJECT_NAME} " \
                              + self.UPGRADE_PATH + "/{BACKUP_PROJECT}"

        self.WEB_INF = "WEB-INF"

        self.rm_file_commend = 'rm -rf ' + self.UPGRADE_PATH + "/{BACKUP_PROJECT}"

        current_date = datetime.datetime.now()
        year = str(current_date.year)
        day = str(current_date.month).zfill(2) + str(current_date.day).zfill(2)
        hour = str(current_date.hour).zfill(2) + str(current_date.minute).zfill(2)
        self.project_list = []
        for up in upgrade_project:
            backup_file_name = up + "-Root-" + year + "-" + day + "-" + hour
            project = Project(up, backup_file_name, os.path.join(self.LOCAL_UPGRADE_FILE, up),
                              os.path.join(self.UPGRADE_PATH, backup_file_name))
            self.project_list.append(project)

        pass


def get_ip_config(file_name):
    with open(file_name, 'r', encoding='utf8') as f:
        data = json.load(f)
        return data


def upload_upgrade_file(local_file_obj, sftp):
    print(local_file_obj)
    children = os.listdir(local_file_obj.localPath)
    for child in children:
        child = os.path.join(local_file_obj.localPath, child)
        print(child)
        if os.path.isdir(child):
            _upload_dir(child, local_file_obj, sftp)
        else:
            _upload_file(child, local_file_obj, sftp)
    pass


def _upload_dir(local_path, local_file_obj, sftp):
    local_path_list = os.path.split(local_path)
    os.chdir(local_path_list[0])
    parent = local_path_list[1]
    for walker in os.walk(parent):
        print('walker:', walker)
        remote_file_path = os.path.join(local_file_obj.remoteTargetPath, walker[0])
        if not sftp.exists(remote_file_path):
            print('remote mkdir : ', remote_file_path)
            sftp.mkdir(remote_file_path)

        for file in walker[2]:
            if file.endswith('.DS_Store'):
                continue
            local_file = os.path.join(walker[0], file)
            remote_file = os.path.join(local_file_obj.remoteTargetPath, walker[0], file)
            print('local_file:', local_file)
            print('remote_file:', remote_file)
            sftp.put(local_file, remote_file)
        print()


def _upload_file(local_file, local_file_obj, sftp):
    local_path_list = os.path.split(local_file)
    remote_file = os.path.join(local_file_obj.remoteTargetPath, local_path_list[1])
    print('local_file:', local_file)
    print('remote_file:', remote_file)
    sftp.put(local_file, remote_file)


def restart_remote_server(sftp):
    commend = '/app/tomcat/bin/shutdown.sh'
    print(sftp.execute(commend))
    time.sleep(3)
    commend = '/bin/bash /app/tomcat/bin/startup.sh'
    print(sftp.execute(commend))
    commend = 'ps -ef | grep tomcat'
    print(sftp.execute(commend))


def backup_file(sftp, backup_commend, project):
    print("***************backup file start***************")
    commend = backup_commend.replace("{PROJECT_NAME}", project.name).replace("{BACKUP_PROJECT}", project.backupFile)
    sftp.execute(commend)
    print("***************backup file end***************\n")


def cp_file_to_webapp(project, conf, sftp):
    print('***************cp upgrade file to normal***************')
    remote_file_list = sftp.listdir(project.remoteTargetPath)
    for file in remote_file_list:
        commend = 'cp -r ' + os.path.join(conf.UPGRADE_PATH, project.backupFile, file) + " " + os.path.join(
            conf.WEBAPP_PATH, project.name)
        print(commend)
        sftp.execute(commend)
    print('***************cp upgrade file to normal***************\n')
    pass


def upgrade(conf, ip_config):
    print("ip:", ip_config, "-start")
    try:
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(host=ip_config['ip'], username=conf.USER, password=conf.PASSWORD, cnopts=cnopts) as sftp:
            # with pysftp.Connection(ip, username=conf.USER, password=conf.PASSWORD) as sftp:
            for project in conf.project_list:
                # 备份文件
                backup_file(sftp, conf.backup_commend, project)
                # 将待升级文件上传至upgrade文件中
                upload_upgrade_file(project, sftp)
                # 复制文件
                cp_file_to_webapp(project, conf, sftp)

                # sftp.excute("rm -rf /app/webapp/portal/WEB-INF/classes/com/xcalculas/portal/controller")
            # print('***************restart remote(' + ip + ') server start***************')
            # # 重启服务器
            # restart_remote_server(sftp)
            # print('***************restart remote(' + ip + ') server end***************\n')
    except BaseException as e:
        print(e)

    print("ip:", ip_config, "-end \n")


def main():
    ip_map = get_ip_config("deploy_local.json")
    upgrade_conf = UpgradeConf('deploy-local.ini')
    shopIdList = upgrade_conf.shopIdList
    del upgrade_conf.shopIdList

    for shopId in shopIdList:
        upgrade(upgrade_conf, ip_map[shopId])

    # with futures.ProcessPoolExecutor() as executor:
    #     for ip_config in IP_List:
    #         executor.submit(upgrade, upgrade_conf, ip_config)

    # for ip_config in IP_List:
    #

    # ip = '192.169.0.19'
    # get_app_log_from_server(upgrade_conf, ip)


if __name__ == '__main__':
    main()
    pass
