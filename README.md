##Установка
Скачать файлы.
Скопировать settings на уровень выше.
```console
cp settings_example.ini ../settings.ini
```
##Авторизация
Авторизация реализована через Implicit Flow:
https://vk.com/dev/implicit_flow_user?f=3.%20%D0%9F%D0%BE%D0%BB%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D0%B5%20access_token
Необходимо заполнить VK_CLIENT_ID в settings.ini
После этого запустить auth_get_code
```console
python auth_get_code.py
```
и в браузере разрешить доступ
В url открывшейся страницы будет токен и id пользователя, их необходимо добавить в settings.ini
##Файлы данных
Имена файлов прописаны в settings, можно менять там.
В groups пишутся через запятую идентификаторы групп (то, что после последней косой черты).
В boards - айдишники обсуждений (если адрес обсуждения https://vk.com/topic-63095842_34608031, то 63095842_34608031)
В images - айди изображений (если адрес изображения https://vk.com/photo59610393_230289330, то в файле photo59610393_230289330)
text - понятно, текст.
После того, как все готово, можно запускать publish:
```console
python -W ignore publish.py
```
Результат в файле log.txt рядом с settings.ini
