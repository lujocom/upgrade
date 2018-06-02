# encoding=utf-8
import configparser
import datetime
import time
from concurrent import futures

import paramiko, os
from collections import namedtuple
import pysftp

PORT = 22
USER = 'wjf'
PASSWORD = "cdyx001@wjf"
# IP_LIST = ['10.8.0.42', '10.8.0.30', '10.8.0.18', '10.8.0.6', '10.8.0.34', '10.8.0.14', '10.8.0.54']
# IP_LIST = ['10.8.0.54']
# IP_LIST = ['10.8.0.6']
# IP_LIST = ['192.168.0.11', '192.168.0.12']
IP_LIST = ['192.168.0.12']
# IP_LIST = ['10.8.0.18', '10.8.0.58']


# upgrade_project = ['portal']
# upgrade_project = ['portal', 'kvs']
upgrade_project = ['kvs']

# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/portal/WEB-INF',
#                              '/Users/luohui/Desktop/upgrade-local/kvs/WEB-INF']
# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/kvs/WEB-INF']
# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/portal/WEB-INF']

WEBAPP_PATH = '/app/webapp'
UPGRADE_PATH = "/app/upgrade"
BACKUP_PATH = "/app/backup"
LOG_PATH = '/logs/applog/'
LOCAL_UPGRADE_FILE = "/Users/luohui/Desktop/upgrade-local/"
backup_commend = "cd /app && cp -r webapp/{PROJECT_NAME} " + BACKUP_PATH \
                 + "/{BACKUP_PROJECT} && cp -r webapp/{PROJECT_NAME} " \
                 + UPGRADE_PATH + "/{BACKUP_PROJECT}"
WEB_INF = "WEB-INF"

rm_file_commend = 'rm -rf ' + UPGRADE_PATH + "/{BACKUP_PROJECT}"

current_date = datetime.datetime.now()
year = str(current_date.year)
day = str(current_date.month).zfill(2) + str(current_date.day)
project_list = []
Project = namedtuple("Project", "name backupFile localPath remoteTargetPath")
for up in upgrade_project:
    backup_file_name = up + "-" + year + "-" + day
    project = Project(up, backup_file_name, os.path.join(LOCAL_UPGRADE_FILE, up),
                      os.path.join(UPGRADE_PATH, backup_file_name))
    project_list.append(project)


def backup_file(ip):
    print("***************backup file start***************")
    for p in project_list:
        commend = backup_commend.replace("{PROJECT_NAME}", p.name).replace("{BACKUP_PROJECT}", p.backupFile)
        _execute_command(ip, USER, PASSWORD, commend)
    print("***************backup file end***************\n")


def rm_file(isAll):
    print("***************rm file start***************")
    for ip in IP_LIST:
        for p in project_list:
            if isAll:
                commend = rm_file_commend.replace("{BACKUP_PROJECT}", p.backupFile)
            else:
                commend = rm_file_commend.replace("{BACKUP_PROJECT}", p.backupFile)
                commend = os.path.join(commend, WEB_INF, "classes/com")
            _execute_command(ip, USER, PASSWORD, commend)
    print("***************rm file end***************\n")


def _execute_command(ip, user, password, commend):
    print("execute_command host start: ", ip)
    print("commend:", commend)
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, PORT, user, password)
        stdin, stdout, stderr = ssh.exec_command(commend)
        print(stdout.read())
    print("execute_command host end: ", ip)


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

        # try:
        #     remote_file_list = sftp.listdir(remote_file_path)
        #     print('remote list dir:', remote_file_list)
        # except:
        #     print('remote mkdir : ', remote_file_path)
        #     sftp.mkdir(remote_file_path)

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


def upload_upgrade_file(ip):
    print('***************ip:', ip, " start upload***************")
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        for local_file in project_list:
            shh_put_all_by_pysftp(local_file, sftp)
    print('***************ip:', ip, " end upload***************\n")
    pass


def get_app_log_from_server(ip):
    # remote_log_path = '/logs/applog/2018-05-29/jcdyx_011'
    remote_log_path = '/logs/applog/2018-05-24/jtest1_1001'
    local_path = '/Users/luohui/Desktop/applog/jtest1_1001'
    print('***************ip:', ip, " start upload***************")
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        get_file(sftp, remote_log_path, local_path)
    print('***************ip:', ip, " end upload***************\n")
    pass


def get_file(sftp, remote_path, local_path):
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
            get_file(sftp, remote_file, local_file)
    if sftp.isfile(remote_path):
        print('get from ', remote_path, " to ", local_path)
        print(sftp.get(remote_path, local_path))
        print()
        return


def cp_file_to_webapp(ip):
    print('***************cp upgrade file to normal***************')
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        for local_file in project_list:
            remote_file_list = sftp.listdir(local_file.remoteTargetPath)
            for file in remote_file_list:
                commend = 'cp -r ' + os.path.join(UPGRADE_PATH, local_file.backupFile, file) + " " + os.path.join(
                    WEBAPP_PATH, local_file.name)
                print(commend)
                sftp.execute(commend)
    print('***************cp upgrade file to normal***************\n')
    pass


def cp_file_to_tomcat(ip):
    print('***************cp config file to tomcat***************')
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        print(ip + "-- > 连接成功")
        print(sftp.put(LOCAL_UPGRADE_FILE + '/catalina.sh', '/app/tomcat/bin/catalina.sh'))
    print('***************cp config file to tomcat***************\n')
    pass


def get_file_from_tomcat(ip):
    print('***************cp config file to tomcat***************')
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        print(ip + "-- > 连接成功")
        print(sftp.get('/app/tomcat/bin/catalina.sh', LOCAL_UPGRADE_FILE + '/catalina.sh'))
    print('***************cp config file to tomcat***************\n')
    pass


def restart_remote_server(ip):
    print('***************restart remote(' + ip + ') server start***************')
    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        commend = '/app/tomcat/bin/shutdown.sh'
        print(sftp.execute(commend))
        time.sleep(3)
        commend = '/bin/bash /app/tomcat/bin/startup.sh'
        print(sftp.execute(commend))
        commend = 'ps -ef | grep tomcat'
        print(sftp.execute(commend))
    print('***************restart remote(' + ip + ') server end***************\n')


def main():
    with futures.ProcessPoolExecutor() as executor:
        # 备份文件
        # executor.map(backup_file, IP_LIST)
        # 将待升级文件上传至upgrade文件中
        # executor.map(upload_upgrade_file, IP_LIST)
        # 将待升级文件copy至正式文件
        # executor.map(cp_file_to_webapp, IP_LIST)
        # 重启服务器
        executor.map(restart_remote_server, IP_LIST)
        # executor.map(get_app_log_from_server, IP_LIST)


if __name__ == '__main__':
    # rm_file(True)
    # backup_file()
    # rm_file(False)
    # upload_upgrade_file()
    # cp_file_to_webapp()
    # restart_server()
    config = configparser.ConfigParser()
    config.read("upgrade.ini")
    print(config.get('global', 'project_name').split(','))
    print(config.get('local', 'project_dir'))
    print(config.get('remote', 'hostname'))
    print(config.get('remote', 'app_log_path'))
    # main()
    pass
