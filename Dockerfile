FROM public.ecr.aws/lambda/python:3.12

COPY . ./

RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

CMD ["app.save_note"]