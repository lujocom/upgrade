# encoding=utf-8
import configparser
import datetime
import time
from concurrent import futures

import paramiko, os
from collections import namedtuple
import pysftp


def _upload_file(local_file, local_file_obj, sftp):
    local_path_list = os.path.split(local_file)
    remote_file = os.path.join(local_file_obj.remoteTargetPath, local_path_list[1])
    print('local_file:', local_file)
    print('remote_file:', remote_file)
    sftp.put(local_file, remote_file)


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


def shh_put_all_by_pysftp(local_file_obj, sftp):
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


class Upgrade:

    def __init__(self, config_file_name):
        self.__config_file_name = config_file_name
        config = configparser.ConfigParser()
        config.read(config_file_name)
        self.PORT = config.get('remote', 'port')
        self.USER = config.get('remote', 'username')
        self.PASSWORD = config.get('remote', 'password')
        self.WEBAPP_PATH = config.get('remote', 'webapp_path')
        self.UPGRADE_PATH = config.get('remote', 'pre_upgrade_path')
        self.BACKUP_PATH = config.get('remote', 'backup_path')
        self.LOG_PATH = config.get('remote', 'app_log_path')
        self.LOCAL_UPGRADE_FILE = config.get('local', 'project_dir')
        self.IP_LIST = config.get('remote', 'hostname').split(',')

        self.upgrade_project = config.get('global', 'project_name')
        self.backup_commend = "cd /app && cp -r webapp/{PROJECT_NAME} " + self.BACKUP_PATH \
                              + "/{BACKUP_PROJECT} && cp -r webapp/{PROJECT_NAME} " \
                              + self.UPGRADE_PATH + "/{BACKUP_PROJECT}"

        self.WEB_INF = "WEB-INF"

        self.rm_file_commend = 'rm -rf ' + self.UPGRADE_PATH + "/{BACKUP_PROJECT}"

        current_date = datetime.datetime.now()
        year = str(current_date.year)
        day = str(current_date.month).zfill(2) + str(current_date.day)
        self.project_list = []
        Project = namedtuple("Project", "name backupFile localPath remoteTargetPath")
        for up in self.upgrade_project:
            backup_file_name = up + "-" + year + "-" + day
            project = Project(up, backup_file_name, os.path.join(self.LOCAL_UPGRADE_FILE, up),
                              os.path.join(self.UPGRADE_PATH, backup_file_name))
            self.project_list.append(project)

        pass

    def upgrade(self):
        with futures.ProcessPoolExecutor() as executor:
            # 备份文件
            # executor.map(backup_file, IP_LIST)
            # 将待升级文件上传至upgrade文件中
            # executor.map(upload_upgrade_file, IP_LIST)
            # 将待升级文件copy至正式文件
            # executor.map(cp_file_to_webapp, IP_LIST)
            # 重启服务器
            executor.map(self.restart_remote_server, self.IP_LIST)
            # executor.map(get_app_log_from_server, IP_LIST)

    def backup_file(self, ip):
        print("***************backup file start***************")
        for p in self.project_list:
            commend = self.backup_commend.replace("{PROJECT_NAME}", p.name).replace("{BACKUP_PROJECT}", p.backupFile)
            self._execute_command(ip, self.USER, self.PASSWORD, commend)
        print("***************backup file end***************\n")

    def rm_file(self, isAll):
        print("***************rm file start***************")
        for ip in self.IP_LIST:
            for p in self.project_list:
                if isAll:
                    commend = self.rm_file_commend.replace("{BACKUP_PROJECT}", p.backupFile)
                else:
                    commend = self.rm_file_commend.replace("{BACKUP_PROJECT}", p.backupFile)
                    commend = os.path.join(commend, self.WEB_INF, "classes/com")
                self._execute_command(ip, self.USER, self.PASSWORD, commend)
        print("***************rm file end***************\n")

    def _execute_command(self, ip, user, password, commend):
        print("execute_command host start: ", ip)
        print("commend:", commend)
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, self.PORT, user, password)
            stdin, stdout, stderr = ssh.exec_command(commend)
            print(stdout.read())
        print("execute_command host end: ", ip)

    def upload_upgrade_file(self, ip):
        print('***************ip:', ip, " start upload***************")
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            for local_file in self.project_list:
                shh_put_all_by_pysftp(local_file, sftp)
        print('***************ip:', ip, " end upload***************\n")
        pass

    def get_app_log_from_server(self, ip):
        # remote_log_path = '/logs/applog/2018-05-29/jcdyx_011'
        remote_log_path = '/logs/applog/2018-05-24/jtest1_1001'
        local_path = '/Users/luohui/Desktop/applog/jtest1_1001'
        print('***************ip:', ip, " start upload***************")
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            self.get_file(sftp, remote_log_path, local_path)
        print('***************ip:', ip, " end upload***************\n")
        pass

    def get_file(self, sftp, remote_path, local_path):
        if sftp.isdir(remote_path):
            if not os.path.exists(local_path):
                os.mkdir(local_path)
            remote_path_list = sftp.listdir(remote_path)
            print(remote_path_list)
            for path in remote_path_list:
                remote_file = os.path.join(remote_path, path)
                local_file = os.path.join(local_path, path)
                print('remote path : ', remote_file)
                print('local path : ', local_file)
                self.get_file(sftp, remote_file, local_file)
        if sftp.isfile(remote_path):
            print('get from ', remote_path, " to ", local_path)
            print(sftp.get(remote_path, local_path))
            print()
            return

    def cp_file_to_webapp(self, ip):
        print('***************cp upgrade file to normal***************')
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            for local_file in self.project_list:
                remote_file_list = sftp.listdir(local_file.remoteTargetPath)
                for file in remote_file_list:
                    commend = 'cp -r ' + os.path.join(self.UPGRADE_PATH, local_file.backupFile,
                                                      file) + " " + os.path.join(
                        self.WEBAPP_PATH, local_file.name)
                    print(commend)
                    sftp.execute(commend)
        print('***************cp upgrade file to normal***************\n')
        pass

    def cp_file_to_tomcat(self, ip):
        print('***************cp config file to tomcat***************')
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            print(ip + "-- > 连接成功")
            print(sftp.put(self.LOCAL_UPGRADE_FILE + '/catalina.sh', '/app/tomcat/bin/catalina.sh'))
        print('***************cp config file to tomcat***************\n')
        pass

    def get_file_from_tomcat(self, ip):
        print('***************cp config file to tomcat***************')
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            print(ip + "-- > 连接成功")
            print(sftp.get('/app/tomcat/bin/catalina.sh', self.LOCAL_UPGRADE_FILE + '/catalina.sh'))
        print('***************cp config file to tomcat***************\n')
        pass

    def restart_remote_server(self, ip):
        print('***************restart remote(' + ip + ') server start***************')
        with pysftp.Connection(ip, username=self.USER, password=self.PASSWORD) as sftp:
            commend = '/app/tomcat/bin/shutdown.sh'
            print(sftp.execute(commend))
            time.sleep(3)
            commend = '/bin/bash /app/tomcat/bin/startup.sh'
            print(sftp.execute(commend))
            commend = 'ps -ef | grep tomcat'
            print(sftp.execute(commend))
        print('***************restart remote(' + ip + ') server end***************\n')


if __name__ == '__main__':
    # rm_file(True)
    # backup_file()
    # rm_file(False)
    # upload_upgrade_file()
    # cp_file_to_webapp()
    # restart_server()
    # config = configparser.ConfigParser()
    # config.read("upgrade.ini")
    # print(config.get('global', 'project_name').split(','))
    # print(config.get('local', 'project_dir'))
    # print(config.get('remote', 'hostname'))
    # print(config.get('remote', 'app_log_path'))
    # main()
    upgrade = Upgrade('upgrade.ini')
    upgrade.upgrade()
    pass
