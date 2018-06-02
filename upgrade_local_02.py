# encoding=utf-8
import datetime

import paramiko, os
from collections import namedtuple
import pysftp

PORT = 22
USER = 'wjf'
PASSWORD = "cdyx001@wjf"
# IP_LIST = ['10.8.0.42', '10.8.0.30', '10.8.0.18', '10.8.0.6', '10.8.0.34', '10.8.0.14', '10.8.0.54']
IP_LIST = ['10.8.0.54']
# IP_LIST = ['10.8.0.42']
# IP_LIST = ['192.168.0.11']

upgrade_project = ['portal']
# upgrade_project = ['portal', 'kvs']
# upgrade_project = ['kvs']

# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/portal/WEB-INF',
#                              '/Users/luohui/Desktop/upgrade-local/kvs/WEB-INF']
# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/kvs/WEB-INF']
# upgrade_project_file_path = ['/Users/luohui/Desktop/upgrade-local/portal/WEB-INF']

WEBAPP_PATH = '/app/webapp'
UPGRADE_PATH = "/app/upgrade"
BACKUP_PATH = "/app/backup"

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


def backup_file():
    print("***************backup file start***************")
    for ip in IP_LIST:
        for p in project_list:
            commend = backup_commend.replace("{PROJECT_NAME}", p.name).replace("{BACKUP_PROJECT}", p.backupFile)
            execute_command(ip, USER, PASSWORD, commend)
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
            execute_command(ip, USER, PASSWORD, commend)
    print("***************rm file end***************\n")


def execute_command(ip, user, password, commend):
    print("execute_command host start: ", ip)
    print("commend:", commend)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, PORT, user, password)
    ssh.exec_command(commend)
    ssh.close()
    print("execute_command host end: ", ip)


def shh_put_all_by_pysftp(local_file_obj, sftp):
    print(local_file_obj)
    children = os.listdir(local_file_obj.localPath)
    for child in children:
        child = os.path.join(local_file_obj.localPath, child)
        print(child)
        if os.path.isdir(child):
            upload_dir(child, local_file_obj, sftp)
        else:
            upload_file(child, local_file_obj, sftp)
    pass


def upload_dir(local_path, local_file_obj, sftp):
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


def upload_file(local_file, local_file_obj, sftp):
    local_path_list = os.path.split(local_file)
    remote_file = os.path.join(local_file_obj.remoteTargetPath, local_path_list[1])
    print('local_file:', local_file)
    print('remote_file:', remote_file)
    sftp.put(local_file, remote_file)


def upload_upgrade_file():
    for ip in IP_LIST:
        print('***************ip:', ip, " start upload***************")
        with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
            for local_file in project_list:
                shh_put_all_by_pysftp(local_file, sftp)
        print('***************ip:', ip, " end upload***************\n")
    pass


def cp_file_to_webapp():
    for ip in IP_LIST:
        print('***************cp upgrade file to normal***************')
        with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
            for local_file in project_list:
                remote_file_list = sftp.listdir(local_file.remoteTargetPath)
                for file in remote_file_list:
                    commend = 'cp -r ' + os.path.join(UPGRADE_PATH, local_file.backupFile, file) + " " + os.path.join(
                        WEBAPP_PATH, local_file.name)
                    print(commend)
                    print(sftp.execute(commend))
        print('***************cp upgrade file to normal***************\n')
    pass


def restart_server():
    for ip in IP_LIST:
        print('host:', ip)
        with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
            restart_commend = './shutdown.sh'
            print(sftp.cwd('/app/tomcat/bin/'))
            print(sftp.execute(restart_commend))
            restart_commend = './startup.sh '
            print(sftp.execute(restart_commend))
            print(sftp.pwd())


if __name__ == '__main__':
    # rm_file(True)
    # backup_file()
    # rm_file(False)
    # upload_upgrade_file()
    # cp_file_to_webapp()
    restart_server()
    pass
