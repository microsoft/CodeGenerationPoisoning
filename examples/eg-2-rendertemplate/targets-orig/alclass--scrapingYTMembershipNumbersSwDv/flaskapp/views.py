"""
  docstring
"""
from flask import render_template, g
import models.sa_models.ytchannelsubscribers_samodels as samodels
from sqlalchemy.sql.expression import desc


def newsarticle_view(newsarticleid):
  newsarticle = g.sa_ext_session.query(samodels.NewsArticlesSA). \
    filter(samodels.NewsArticlesSA.id == newsarticleid). \
    first()
  if newsarticle:
    title = newsarticle.title
    title = title if len(title) < 30 else title[:30]
    return render_template('newsarticle_tmpl.html', title=title, newsarticle=newsarticle)
  return list_newsarticles_view()


def list_newsarticles_view():
  news_articles = g.sa_ext_session.query(samodels.NewsArticlesSA). \
    order_by(desc(samodels.NewsArticlesSA.publishdate)). \
    all()
  return render_template('newsarticles_lister_tmpl.html', title='Newspaper Articles', newsarticles=news_articles)


def list_ytchannels_view():
  """
  # order_by(desc(samodels.YTChannelSA.scrapedate)). \
  :return:
  """
  # session = Session()
  ytchannels = g.sa_ext_session.query(samodels.YTChannelSA).order_by(samodels.YTChannelSA.nname).all()
  ytchannels = sorted(ytchannels, key=lambda o: o.most_recent_video.publishdate, reverse=True)
  return render_template('ytchannel_lister_tmpl.html', title='YouTube Channels Observed', ytchannels=ytchannels)


def subscribers_per_channel(ytchannelid):
  N_OF_SUBSCRIBERS_DAYS = 30
  ytchannel = g.sa_ext_session.query(samodels.YTChannelSA). \
    filter(samodels.YTChannelSA.ytchannelid == ytchannelid). \
    first()
  subscribers_list = ytchannel.daily_subscribers
  if subscribers_list.count() > N_OF_SUBSCRIBERS_DAYS:
    subscribers_list = subscribers_list[: N_OF_SUBSCRIBERS_DAYS]  # .query.paginate(1, 20).items
  title_sent = ytchannel.nname + ' Subscribers'
  return render_template(
    'ytchannel_subscribers_tmpl.html', title=title_sent,
    ytchannel=ytchannel, subscribers_list=subscribers_list
  )


def ytchannel_summary(ytchannelid):  # former output_ytchannel_videos
  ytchannel = g.sa_ext_session.query(samodels.YTChannelSA). \
    filter(samodels.YTChannelSA.ytchannelid == ytchannelid). \
    first()
  vinfolist = ytchannel.vinfolist
  if vinfolist.count() > 20:
    vinfolist = ytchannel.vinfolist[: 20]  # .query.paginate(1, 20).items
  title_sent = ytchannel.nname + ' Summary'
  return render_template('ytchannel_summary_tmpl.html', title=title_sent, ytchannel=ytchannel, vinfolist=vinfolist)


def videos_per_channel(ytchannelid):
  ytchannel = g.sa_ext_session.query(samodels.YTChannelSA).\
    filter(samodels.YTChannelSA.ytchannelid == ytchannelid).first()
  title_sent = ytchannel.nname + ' Video Listing and Statistics'
  return render_template('videos_per_channel_tmpl.html', title=title_sent, ytchannel=ytchannel)


def views_per_video(ytvideoid):
  ini = 1
  fim = 20
  vviews = g.sa_ext_session.query(samodels.YTVideoViewsSA).filter(samodels.YTVideoViewsSA.ytvideoid == ytvideoid).\
      paginate(ini, fim, False).items
  return render_template('views_per_video_tmpl.html', title='Views per Video', vviews=vviews)


def newsarticles():
  articles = g.sa_ext_session.query(samodels.NewsArticlesSA).all()
  return render_template('newsarticles_tmpl.html', title='News Articles', articles=articles)


def process():
  pass


if __name__ == '__main__':
  process()
